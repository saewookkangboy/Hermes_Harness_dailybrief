"""Meta Ads loop — 피로도 감시 + 주간 리포트 (조회 전용, 결정적, LLM 0회).

Read-only by construction: the only network call is an HTTP GET to the Insights
endpoint. There is no code path that writes to the ad account; changing budget,
bids, audiences or status stays behind the human approval gate.

Modes
  sample  tests/fixtures/meta/insights_sample.json — no notifications, no Notion
  api     Meta Marketing API, token/account from env or ~/.hermes/.env
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config" / "meta-ads.yaml"
SAMPLE_PATH = REPO_ROOT / "tests" / "fixtures" / "meta" / "insights_sample.json"
INSIGHT_FIELDS = (
    "adset_id,adset_name,campaign_name,impressions,reach,frequency,"
    "clicks,ctr,spend,cpm,cpc,actions"
)


class MetaApiError(RuntimeError):
    pass


# ── config ────────────────────────────────────────────────────────────────
def load_config() -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        cfg = (yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}).get("meta_ads", {})
    except Exception:  # noqa: BLE001
        cfg = {}
    cfg.setdefault("mode", "sample")
    cfg.setdefault("api", {}).setdefault("version", "v25.0")
    cfg["api"].setdefault("level", "adset")
    cfg["api"].setdefault("timeout_seconds", 30)
    cfg.setdefault("currency", "KRW")
    cfg.setdefault("window_days", 7)
    cfg.setdefault("conversion_action_types", ["lead"])
    fat = cfg.setdefault("fatigue", {})
    fat.setdefault("min_impressions", 5000)
    fat.setdefault("max_frequency", 3.5)
    fat.setdefault("ctr_drop_pct", -20)
    cfg.setdefault("outputs", {}).setdefault("dir", "content/ads")
    env_mode = os.environ.get("HERMES_META_ADS_MODE")
    if env_mode:
        cfg["mode"] = env_mode
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


# ── data model ────────────────────────────────────────────────────────────
@dataclass
class AdSetStats:
    adset_id: str
    adset_name: str
    campaign_name: str
    impressions: int = 0
    reach: int = 0
    frequency: float = 0.0
    clicks: int = 0
    ctr: float = 0.0          # percent
    spend: float = 0.0
    conversions: float = 0.0

    @classmethod
    def from_row(cls, row: dict, conversion_types: list[str]) -> "AdSetStats":
        conv = sum(
            float(a.get("value", 0) or 0)
            for a in row.get("actions") or []
            if a.get("action_type") in conversion_types
        )
        impressions = int(float(row.get("impressions", 0) or 0))
        clicks = int(float(row.get("clicks", 0) or 0))
        reach = int(float(row.get("reach", 0) or 0))
        freq = float(row.get("frequency") or (impressions / reach if reach else 0))
        ctr = float(row.get("ctr") or (clicks / impressions * 100 if impressions else 0))
        return cls(
            adset_id=str(row.get("adset_id", "")),
            adset_name=str(row.get("adset_name", "")),
            campaign_name=str(row.get("campaign_name", "")),
            impressions=impressions,
            reach=reach,
            frequency=freq,
            clicks=clicks,
            ctr=ctr,
            spend=float(row.get("spend", 0) or 0),
            conversions=conv,
        )


@dataclass
class Window:
    since: str
    until: str
    rows: list[AdSetStats] = field(default_factory=list)

    def by_id(self) -> dict[str, AdSetStats]:
        return {r.adset_id: r for r in self.rows}


@dataclass
class Insights:
    source: str               # "sample" | "api"
    currency: str
    current: Window
    previous: Window


# ── loading ───────────────────────────────────────────────────────────────
def windows_for(today: date, days: int) -> tuple[tuple[str, str], tuple[str, str]]:
    """Last `days` full days ending yesterday, and the `days` before that."""
    until = today - timedelta(days=1)
    since = until - timedelta(days=days - 1)
    p_until = since - timedelta(days=1)
    p_since = p_until - timedelta(days=days - 1)
    return (since.isoformat(), until.isoformat()), (p_since.isoformat(), p_until.isoformat())


def _get_json(url: str, timeout: int) -> dict:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise MetaApiError(f"HTTP {exc.code}: {detail}") from exc
    except OSError as exc:
        raise MetaApiError(str(exc)) from exc


def _fetch_window(cfg: dict, token: str, account: str, since: str, until: str) -> list[dict]:
    api = cfg["api"]
    params = {
        "level": api["level"],
        "fields": INSIGHT_FIELDS,
        "time_range": json.dumps({"since": since, "until": until}),
        "limit": 200,
        "access_token": token,
    }
    url = f"https://graph.facebook.com/{api['version']}/act_{account}/insights?{urllib.parse.urlencode(params)}"
    rows: list[dict] = []
    while url:
        page = _get_json(url, int(api["timeout_seconds"]))
        if "error" in page:
            raise MetaApiError(str(page["error"])[:300])
        rows.extend(page.get("data") or [])
        url = (page.get("paging") or {}).get("next") or ""
    return rows


def load_insights(cfg: dict, today: date | None = None) -> Insights:
    conv = list(cfg["conversion_action_types"])
    if cfg["mode"] == "sample":
        fx = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
        cur, prev = fx["windows"]["current"], fx["windows"]["previous"]
        return Insights(
            source="sample",
            currency=fx.get("account_currency", cfg["currency"]),
            current=Window(cur["since"], cur["until"], [AdSetStats.from_row(r, conv) for r in cur["data"]]),
            previous=Window(prev["since"], prev["until"], [AdSetStats.from_row(r, conv) for r in prev["data"]]),
        )
    if cfg["mode"] != "api":
        raise MetaApiError(f"unknown mode: {cfg['mode']}")
    token = _env_value("META_ACCESS_TOKEN")
    account = _env_value("META_AD_ACCOUNT_ID").removeprefix("act_")
    if not token or not account:
        raise MetaApiError("META_ACCESS_TOKEN / META_AD_ACCOUNT_ID 가 ~/.hermes/.env 에 없습니다")
    today = today or date.fromisoformat(_studio_today())
    (c_since, c_until), (p_since, p_until) = windows_for(today, int(cfg["window_days"]))
    return Insights(
        source="api",
        currency=cfg["currency"],
        current=Window(c_since, c_until, [AdSetStats.from_row(r, conv) for r in _fetch_window(cfg, token, account, c_since, c_until)]),
        previous=Window(p_since, p_until, [AdSetStats.from_row(r, conv) for r in _fetch_window(cfg, token, account, p_since, p_until)]),
    )


def _studio_today() -> str:
    try:
        from lib.common import studio_today

        return studio_today()
    except Exception:  # noqa: BLE001
        return date.today().isoformat()


# ── fatigue rule (policy lives here, not in a model) ──────────────────────
@dataclass
class FatigueRow:
    cur: AdSetStats
    prev: AdSetStats | None
    ctr_change_pct: float | None
    fatigued: bool
    reason: str


def pct_change(new: float, old: float) -> float | None:
    if not old:
        return None
    return (new - old) / old * 100


def evaluate_fatigue(ins: Insights, cfg: dict) -> list[FatigueRow]:
    f = cfg["fatigue"]
    prev_by_id = ins.previous.by_id()
    out: list[FatigueRow] = []
    for cur in ins.current.rows:
        prev = prev_by_id.get(cur.adset_id)
        change = pct_change(cur.ctr, prev.ctr) if prev else None
        checks = {
            "impressions": cur.impressions >= f["min_impressions"],
            "frequency": cur.frequency >= f["max_frequency"],
            "ctr_drop": change is not None and change <= f["ctr_drop_pct"],
        }
        fatigued = all(checks.values())
        missing = [k for k, ok in checks.items() if not ok]
        reason = "3개 조건 충족" if fatigued else "미충족: " + ", ".join(missing)
        out.append(FatigueRow(cur, prev, change, fatigued, reason))
    out.sort(key=lambda r: (not r.fatigued, -r.cur.frequency))
    return out


# ── formatting ────────────────────────────────────────────────────────────
def _money(v: float, currency: str) -> str:
    return f"₩{v:,.0f}" if currency == "KRW" else f"{v:,.2f} {currency}"


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{v:+.0f}%"


def source_line(ins: Insights, cfg: dict) -> str:
    f = cfg["fatigue"]
    src = "샘플 데이터(tests/fixtures/meta, 실제 계정 아님)" if ins.source == "sample" else "Meta Ads Insights API"
    return (
        f"출처: {src} · 기간 {ins.current.since}~{ins.current.until} vs {ins.previous.since}~{ins.previous.until} (KST) · "
        f"광고세트 단위 · 판정 조건: 노출≥{f['min_impressions']:,} · 빈도≥{f['max_frequency']} · CTR 변화≤{f['ctr_drop_pct']}%"
    )


def format_fatigue_alert(ins: Insights, rows: list[FatigueRow], cfg: dict) -> str:
    """Slack message. Empty string when nothing is fatigued (post nothing)."""
    flagged = [r for r in rows if r.fatigued]
    if not flagged:
        return ""
    lines = [f"[Meta 피로도] 광고세트 {len(flagged)}개 소재 교체 검토 필요"]
    for r in flagged:
        prev_ctr = f"{r.prev.ctr:.2f}%" if r.prev else "—"
        lines.append(
            f"• {r.cur.adset_name} ({r.cur.campaign_name}) · 빈도 {r.cur.frequency:.1f} · "
            f"CTR {prev_ctr}→{r.cur.ctr:.2f}% ({_pct(r.ctr_change_pct)}) · 노출 {r.cur.impressions:,}"
        )
    lines.append(source_line(ins, cfg))
    lines.append("예산·입찰·오디언스·상태는 바꾸지 않았습니다. 소재 교체는 광고 관리자에서 직접 진행해 주세요.")
    return "\n".join(lines)


def totals(w: Window, conv_label: str = "") -> dict[str, float]:
    imp = sum(r.impressions for r in w.rows)
    clicks = sum(r.clicks for r in w.rows)
    spend = sum(r.spend for r in w.rows)
    conv = sum(r.conversions for r in w.rows)
    return {
        "spend": spend,
        "impressions": imp,
        "clicks": clicks,
        "ctr": clicks / imp * 100 if imp else 0.0,
        "cpc": spend / clicks if clicks else 0.0,
        "cpm": spend / imp * 1000 if imp else 0.0,
        "conversions": conv,
        "cpa": spend / conv if conv else 0.0,
    }


def format_weekly_report(ins: Insights, rows: list[FatigueRow], cfg: dict) -> str:
    cur, prev = totals(ins.current), totals(ins.previous)
    cc = ins.currency
    sample_note = "\n> 샘플 데이터로 만든 리포트입니다. 실제 계정 수치가 아닙니다.\n" if ins.source == "sample" else ""
    kpis = [
        ("지출", _money(cur["spend"], cc), _money(prev["spend"], cc), pct_change(cur["spend"], prev["spend"])),
        ("노출", f"{cur['impressions']:,.0f}", f"{prev['impressions']:,.0f}", pct_change(cur["impressions"], prev["impressions"])),
        ("클릭", f"{cur['clicks']:,.0f}", f"{prev['clicks']:,.0f}", pct_change(cur["clicks"], prev["clicks"])),
        ("CTR", f"{cur['ctr']:.2f}%", f"{prev['ctr']:.2f}%", pct_change(cur["ctr"], prev["ctr"])),
        ("CPC", _money(cur["cpc"], cc), _money(prev["cpc"], cc), pct_change(cur["cpc"], prev["cpc"])),
        ("CPM", _money(cur["cpm"], cc), _money(prev["cpm"], cc), pct_change(cur["cpm"], prev["cpm"])),
        ("전환", f"{cur['conversions']:,.0f}", f"{prev['conversions']:,.0f}", pct_change(cur["conversions"], prev["conversions"])),
        ("CPA", _money(cur["cpa"], cc) if cur["conversions"] else "—",
         _money(prev["cpa"], cc) if prev["conversions"] else "—", pct_change(cur["cpa"], prev["cpa"])),
    ]
    flagged = [r for r in rows if r.fatigued]
    out = [
        f"# Meta Ads 주간 리포트 · {ins.current.since} ~ {ins.current.until}",
        sample_note,
        "## 요약",
        "",
        f"지출 {_money(cur['spend'], cc)}({_pct(pct_change(cur['spend'], prev['spend']))}), "
        f"전환 {cur['conversions']:,.0f}건({_pct(pct_change(cur['conversions'], prev['conversions']))}), "
        f"피로도 교체 검토 광고세트 {len(flagged)}개.",
        "",
        "| 지표 | 최근 7일 | 직전 7일 | 변화 |",
        "| --- | --- | --- | --- |",
        *[f"| {k} | {a} | {b} | {_pct(c)} |" for k, a, b, c in kpis],
        "",
        "## 광고세트별 (지출 순)",
        "",
        "| 광고세트 | 캠페인 | 지출 | 노출 | 빈도 | CTR (변화) | 전환 | 피로도 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in sorted(rows, key=lambda x: -x.cur.spend):
        c = r.cur
        out.append(
            f"| {c.adset_name} | {c.campaign_name} | {_money(c.spend, cc)} | {c.impressions:,} | "
            f"{c.frequency:.1f} | {c.ctr:.2f}% ({_pct(r.ctr_change_pct)}) | {c.conversions:,.0f} | "
            f"{'교체 검토' if r.fatigued else '—'} |"
        )
    out += ["", "## 조건과 출처", "", f"- {source_line(ins, cfg)}",
            f"- 전환 기준 action_type: {', '.join(cfg['conversion_action_types'])}",
            "- 이 리포트는 조회만 했고 광고 계정에 어떤 변경도 하지 않았습니다.", ""]
    return "\n".join(out)


def output_path(kind: str, ins: Insights, cfg: dict, today: str | None = None) -> Path:
    stamp = today or _studio_today()
    workdir = Path(os.environ.get("HERMES_WORKDIR", REPO_ROOT))
    base = workdir / cfg["outputs"]["dir"]
    # "_" prefix: archive-to-notion.py skips it, so sample runs never reach Notion
    prefix = "_sample_" if ins.source == "sample" else ""
    name = {"fatigue": "meta-fatigue", "weekly": "meta-weekly-report"}[kind]
    return base / f"{prefix}{stamp}_{name}.md"
