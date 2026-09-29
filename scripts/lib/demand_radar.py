"""네이버 데이터랩 수요 레이더 — 급상승 키워드 제안 (결정적, LLM 0회).

The DataLab Search Trend API is a read-only query (HTTP POST with a JSON body).
Ratios are relative (the largest value in one request = 100), so the radar only
compares a keyword with its own history: last week vs the previous N-week mean.
Suggestions go to Slack; nothing is merged into M1 automatically.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config" / "demand-radar.yaml"
SAMPLE_PATH = REPO_ROOT / "tests" / "fixtures" / "datalab" / "search_trend_sample.json"
MAX_GROUPS_PER_REQUEST = 5
SPARK = "▁▂▃▄▅▆▇█"


class DataLabError(RuntimeError):
    pass


# ── config ────────────────────────────────────────────────────────────────
def load_config() -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        cfg = (yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}).get("demand_radar", {})
    except Exception:  # noqa: BLE001
        cfg = {}
    cfg.setdefault("mode", "sample")
    api = cfg.setdefault("api", {})
    api.setdefault("provider", "hub")
    api.setdefault("hub_url", "https://naverapihub.apigw.ntruss.com/search-trend/v1/search")
    api.setdefault("legacy_url", "https://openapi.naver.com/v1/datalab/search")
    api.setdefault("timeout_seconds", 20)
    cfg.setdefault("lookback_weeks", 12)
    cfg.setdefault("baseline_weeks", 4)
    r = cfg.setdefault("rising", {})
    r.setdefault("min_growth_pct", 30)
    r.setdefault("min_baseline_ratio", 2.0)
    r.setdefault("max_suggestions", 5)
    cfg.setdefault("themes", {})
    cfg.setdefault("outputs", {}).setdefault("dir", "content/signals")
    if os.environ.get("HERMES_DEMAND_RADAR_MODE"):
        cfg["mode"] = os.environ["HERMES_DEMAND_RADAR_MODE"]
    return cfg


def _env_value(key: str) -> str:
    if os.environ.get(key):
        return os.environ[key].strip()
    env_file = Path(os.environ.get("HERMES_ENV", Path.home() / ".hermes" / ".env"))
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


# ── periods ───────────────────────────────────────────────────────────────
def week_range(today: date, weeks: int) -> tuple[str, str]:
    """`weeks` full Monday–Sunday weeks ending with last week."""
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(weeks=1)
    start = last_monday - timedelta(weeks=weeks - 1)
    return start.isoformat(), (last_monday + timedelta(days=6)).isoformat()


def periods(start: str, weeks: int) -> list[str]:
    s = date.fromisoformat(start)
    return [(s + timedelta(weeks=i)).isoformat() for i in range(weeks)]


def series_from_result(result: dict, period_list: list[str]) -> list[float]:
    """Missing periods mean zero searches in DataLab responses."""
    by_period = {d["period"]: float(d["ratio"]) for d in result.get("data") or []}
    return [by_period.get(p, 0.0) for p in period_list]


# ── API ───────────────────────────────────────────────────────────────────
def _post(cfg: dict, body: dict) -> dict:
    api = cfg["api"]
    if api["provider"] == "legacy":
        url = api["legacy_url"]
        headers = {"X-Naver-Client-Id": _env_value("NAVER_CLIENT_ID"),
                   "X-Naver-Client-Secret": _env_value("NAVER_CLIENT_SECRET")}
    else:
        url = api["hub_url"]
        headers = {"X-NCP-APIGW-API-KEY-ID": _env_value("NAVER_HUB_API_KEY_ID"),
                   "X-NCP-APIGW-API-KEY": _env_value("NAVER_HUB_API_KEY")}
    if not all(headers.values()):
        raise DataLabError(f"데이터랩 키가 ~/.hermes/.env 에 없습니다 ({', '.join(headers)})")
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",  # DataLab queries are POST-with-body; nothing is written
    )
    try:
        with urllib.request.urlopen(req, timeout=int(api["timeout_seconds"])) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        raise DataLabError(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}") from exc
    except OSError as exc:
        raise DataLabError(str(exc)) from exc


def _query(cfg: dict, start: str, end: str, groups: list[tuple[str, list[str]]]) -> dict:
    body = {
        "startDate": start,
        "endDate": end,
        "timeUnit": "week",
        "keywordGroups": [{"groupName": name, "keywords": kws[:20]} for name, kws in groups],
    }
    return _post(cfg, body)


# ── model ─────────────────────────────────────────────────────────────────
@dataclass
class KeywordTrend:
    keyword: str
    theme: str
    series: list[float]
    last: float
    baseline: float
    growth_pct: float | None
    rising: bool


@dataclass
class RadarResult:
    source: str
    start: str
    end: str
    keywords: list[KeywordTrend]
    themes: list[KeywordTrend]

    @property
    def rising(self) -> list[KeywordTrend]:
        return [k for k in self.keywords if k.rising]


def _trend(name: str, theme: str, series: list[float], cfg: dict, *, apply_rule: bool = True) -> KeywordTrend:
    n = int(cfg["baseline_weeks"])
    last = series[-1] if series else 0.0
    window = series[-1 - n:-1] if len(series) > n else series[:-1]
    base = sum(window) / len(window) if window else 0.0
    growth = (last - base) / base * 100 if base else None
    r = cfg["rising"]
    rising = apply_rule and growth is not None and base >= r["min_baseline_ratio"] and growth >= r["min_growth_pct"]
    return KeywordTrend(name, theme, series, last, base, growth, rising)


def build_radar(cfg: dict, today: date | None = None) -> RadarResult:
    weeks = int(cfg["lookback_weeks"])
    if cfg["mode"] == "sample":
        fx = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
        start = fx["theme_overview"]["startDate"]
        end = fx["theme_overview"]["endDate"]
        plist = periods(start, weeks)
        kw_results = [(theme, res) for theme, resp in fx["themes"].items() for res in resp["results"]]
        theme_results = fx["theme_overview"]["results"]
        source = "sample"
    elif cfg["mode"] == "api":
        today = today or _today()
        start, end = week_range(today, weeks)
        plist = periods(start, weeks)
        kw_results = []
        for theme, kws in cfg["themes"].items():
            for i in range(0, len(kws), MAX_GROUPS_PER_REQUEST):
                chunk = [(k, [k]) for k in kws[i:i + MAX_GROUPS_PER_REQUEST]]
                resp = _query(cfg, start, end, chunk)
                kw_results += [(theme, res) for res in resp.get("results") or []]
        theme_groups = [(t, list(k)) for t, k in cfg["themes"].items()][:MAX_GROUPS_PER_REQUEST]
        theme_results = _query(cfg, start, end, theme_groups).get("results") or []
        source = "api"
    else:
        raise DataLabError(f"unknown mode: {cfg['mode']}")

    keywords = [_trend(res["title"], theme, series_from_result(res, plist), cfg) for theme, res in kw_results]
    keywords.sort(key=lambda k: (not k.rising, -(k.growth_pct or -1e9)))
    cap = int(cfg["rising"]["max_suggestions"])
    for extra in [k for k in keywords if k.rising][cap:]:
        extra.rising = False
    themes = [_trend(res["title"], res["title"], series_from_result(res, plist), cfg, apply_rule=False) for res in theme_results]
    return RadarResult(source, start, end, keywords, themes)


def _today() -> date:
    try:
        from lib.common import studio_today

        return date.fromisoformat(studio_today())
    except Exception:  # noqa: BLE001
        return date.today()


# ── formatting ────────────────────────────────────────────────────────────
def spark(series: list[float]) -> str:
    hi = max(series) if series else 0
    if not hi:
        return SPARK[0] * len(series)
    return "".join(SPARK[min(len(SPARK) - 1, int(v / hi * (len(SPARK) - 1)))] for v in series)


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{v:+.0f}%"


def last_week_label(r: RadarResult) -> str:
    end = date.fromisoformat(r.end)
    return f"{(end - timedelta(days=6)).isoformat()}~{r.end}"


def source_line(r: RadarResult, cfg: dict) -> str:
    rr = cfg["rising"]
    src = "샘플 데이터(tests/fixtures/datalab, 실제 수치 아님)" if r.source == "sample" else "네이버 데이터랩 통합 검색어 트렌드"
    return (
        f"출처: {src} · 기간 {r.start}~{r.end} 주 단위 · 전체 기기·성별·연령 · "
        f"급상승: 지난주 ÷ 직전 {cfg['baseline_weeks']}주 평균 ≥ +{rr['min_growth_pct']}% (기준값 ≥ {rr['min_baseline_ratio']}) · "
        "ratio는 요청 내 최대값 100 기준 상대값이라 키워드 간 검색량 비교가 아닙니다"
    )


def format_slack(r: RadarResult, cfg: dict, report_name: str) -> str:
    label = "[샘플] " if r.source == "sample" else ""
    if not r.rising:
        return f"{label}[수요 레이더] {last_week_label(r)} 급상승 키워드 없음 · {report_name}"
    lines = [f"{label}[수요 레이더] {last_week_label(r)} 급상승 {len(r.rising)}개 — M1 리서치 후보"]
    for k in r.rising:
        lines.append(f"• {k.keyword} ({k.theme}) {_pct(k.growth_pct)} · {spark(k.series)}")
    lines.append("M1에 넣으려면 골라서 실행: " + " · ".join(f"/research {k.keyword}" for k in r.rising))
    lines.append(source_line(r, cfg))
    return "\n".join(lines)


def format_report(r: RadarResult, cfg: dict) -> str:
    out = [f"# 네이버 검색 수요 레이더 · {last_week_label(r)}", ""]
    if r.source == "sample":
        out += ["> 샘플 데이터로 만든 리포트입니다. 실제 네이버 검색 수치가 아닙니다.", ""]
    base_h = f"직전 {cfg['baseline_weeks']}주 평균"
    trend_h = f"{cfg['lookback_weeks']}주 추이"
    out += ["## 급상승 키워드 (M1 후보 제안)", ""]
    if r.rising:
        out += [f"| 키워드 | 테마 | 지난주 | {base_h} | 변화 | {trend_h} |", "| --- | --- | --- | --- | --- | --- |"]
        out += [f"| {k.keyword} | {k.theme} | {k.last:.1f} | {k.baseline:.1f} | {_pct(k.growth_pct)} | {spark(k.series)} |" for k in r.rising]
        out += ["", "M1 리서치에 넣으려면 텔레그램·슬랙에서 직접 실행합니다 (자동 병합하지 않음):", ""]
        out += [f"- `/research {k.keyword}`" for k in r.rising]
    else:
        out.append("이번 주 급상승 키워드는 없습니다.")
    out += ["", "## 테마별 추이", "", f"| 테마 | 지난주 | {base_h} | 변화 | {trend_h} |", "| --- | --- | --- | --- | --- |"]
    out += [f"| {t.keyword} | {t.last:.1f} | {t.baseline:.1f} | {_pct(t.growth_pct)} | {spark(t.series)} |" for t in r.themes]
    out += ["", "## 전체 키워드", "", f"| 키워드 | 테마 | 지난주 | {base_h} | 변화 | 판정 |", "| --- | --- | --- | --- | --- | --- |"]
    for k in sorted(r.keywords, key=lambda x: (x.theme, -(x.growth_pct or -1e9))):
        note = "급상승" if k.rising else ("기준값 작음" if k.baseline < cfg["rising"]["min_baseline_ratio"] else "—")
        out.append(f"| {k.keyword} | {k.theme} | {k.last:.1f} | {k.baseline:.1f} | {_pct(k.growth_pct)} | {note} |")
    out += ["", "## 조건과 출처", "", f"- {source_line(r, cfg)}", ""]
    return "\n".join(out)


def output_path(r: RadarResult, cfg: dict, stamp: str | None = None) -> Path:
    stamp = stamp or _today().isoformat()
    workdir = Path(os.environ.get("HERMES_WORKDIR", REPO_ROOT))
    prefix = "_sample_" if r.source == "sample" else ""
    return workdir / cfg["outputs"]["dir"] / f"{prefix}{stamp}_demand-radar.md"
