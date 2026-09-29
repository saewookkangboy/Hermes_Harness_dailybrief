"""Campaign launch graph — 브리프 → 리서치 → 카피 → 검수 ↺ → 사람 승인 → 런칭 패키지 → 감시 인계.

    load_brief ─▶ research ─▶ copy ─▶ review ─┬─▶ approval ⏸ (사람) ─▶ package ─▶ handoff ─▶ end
         │                     ▲              │
         └─▶ blocked           └── 재작성 ◀───┘ (걸린 변형만, 최대 copy.max_retries회)

- 광고 계정 쓰기 없음. Meta API를 부르지 않습니다. 산출물은 사람이 광고 관리자에 올리는 파일까지입니다.
- 예산·기간·타깃은 CSV에 넣지 않습니다. 광고 관리자 화면에서 사람이 입력합니다.
- 상태는 .harness/campaigns/{id}.json 에 노드마다 저장되고, 승인 대기(approval)에서 멈췄다가
  `캠페인 승인 <id>` (또는 hermes-agent.sh approve campaign <id>) 로 package부터 이어집니다.
- 승인 뒤 브리프 파일이나 카피가 바뀌면 해시가 달라져 승인이 거부됩니다.

Modes
  sample  tests/fixtures/campaign/copy_sample.json — Codex 호출 없음, 산출물 `_sample_` 접두사(Notion 제외)
  codex   scripts/hermes-run.sh (HERMES_USE_CODEX=1) — loop budget 확인 후 호출, cost ledger 기록
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "campaign-launch.yaml"
TEMPLATE_PATH = REPO_ROOT / "templates" / "campaign" / "brief.example.yaml"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
URL_IN_TEXT_RE = re.compile(r"https?://|www\.", re.I)
TEXT_FIELDS = ("primary_text", "headline", "description")
FIELD_KO = {"primary_text": "본문", "headline": "제목", "description": "설명"}

# 그래프 정의 — 노드와 나갈 수 있는 간선. 실제 이동은 _route()가 상태를 보고 고릅니다.
GRAPH: dict[str, tuple[str, ...]] = {
    "load_brief": ("research", "blocked"),
    "research": ("copy",),
    "copy": ("review", "blocked"),
    "review": ("copy", "approval", "blocked"),
    "approval": ("human",),          # 멈춤 — 사람 승인 뒤 package부터 재개
    "package": ("handoff",),
    "handoff": ("end",),
}
STOP = {"human", "blocked", "end"}
STATUS_KO = {
    "running": "진행 중",
    "blocked": "막힘",
    "awaiting_approval": "승인 대기",
    "approved": "승인됨",
    "packaged": "패키지 완료",
    "rejected": "반려",
}


class CampaignError(RuntimeError):
    pass


# ── config · paths ────────────────────────────────────────────────────────
def load_config() -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        cfg = (yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}).get("campaign_launch", {})
    except Exception:  # noqa: BLE001
        cfg = {}
    cfg.setdefault("mode", "sample")
    cfg.setdefault("briefs_dir", "content/campaigns/briefs")
    cfg.setdefault("outputs_dir", "content/campaigns")
    cfg.setdefault("state_dir", ".harness/campaigns")
    cfg.setdefault("notify", "auto")
    cp = cfg.setdefault("copy", {})
    cp.setdefault("variants", 3)
    cp.setdefault("max_retries", 2)
    cp.setdefault("min_passing", 2)
    cp.setdefault("timeout_sec", 300)
    cp.setdefault("sample_fixture", "tests/fixtures/campaign/copy_sample.json")
    rs = cfg.setdefault("research", {})
    rs.setdefault("max_insights", 3)
    rs.setdefault("radar_glob", "content/signals/*_demand-radar.md")
    cfg.setdefault("objectives", {"leads": "OUTCOME_LEADS", "traffic": "OUTCOME_TRAFFIC"})
    rv = cfg.setdefault("review", {})
    rv.setdefault("recommended_length", {"primary_text": 125, "headline": 40, "description": 30})
    rv.setdefault("require_evidence", ["최고", "최초", "1위", "100%", "보장"])
    rv.setdefault("allow_phrases", [])
    rv.setdefault("needs_conditions", ["무료", "할인"])
    rv.setdefault("placeholders", ["{{", "}}", "TODO", "TBD"])
    rv.setdefault("cta_allowed", ["LEARN_MORE", "SIGN_UP"])
    rv.setdefault("allowed_landing_domains", [])
    rv.setdefault("max_daily_krw", 1_000_000)
    pk = cfg.setdefault("package", {})
    pk.setdefault("status", "PAUSED")
    pk.setdefault("utm", {"source": "meta", "medium": "paid_social"})
    pk.setdefault("columns", {})
    env_mode = os.environ.get("HERMES_CAMPAIGN_MODE")
    if env_mode:
        cfg["mode"] = env_mode
    return cfg


def workdir() -> Path:
    return Path(os.environ.get("HERMES_WORKDIR", REPO_ROOT))


def _state_dir(cfg: dict) -> Path:
    return workdir() / cfg["state_dir"]


def _state_path(cfg: dict, cid: str) -> Path:
    if not ID_RE.match(cid or ""):
        raise CampaignError(f"캠페인 id 형식이 아니에요: {cid!r} (영문 소문자·숫자·하이픈)")
    return _state_dir(cfg) / f"{cid}.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _kst(iso: str) -> str:
    try:
        from zoneinfo import ZoneInfo

        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST")
    except Exception:  # noqa: BLE001
        return iso


def _sha(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def load_state(cfg: dict, cid: str) -> dict[str, Any]:
    path = _state_path(cfg, cid)
    if not path.exists():
        raise CampaignError(f"캠페인 '{cid}'을 찾지 못했어요. `campaign-launch.py status`로 목록을 확인하세요.")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(cfg: dict, state: dict[str, Any]) -> Path:
    path = _state_path(cfg, state["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def list_states(cfg: dict) -> list[dict[str, Any]]:
    d = _state_dir(cfg)
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return out


# ── brief ─────────────────────────────────────────────────────────────────
def resolve_brief_path(cfg: dict, arg: str) -> Path:
    p = Path(arg).expanduser()
    candidates = [p, workdir() / p, workdir() / cfg["briefs_dir"] / p, workdir() / cfg["briefs_dir"] / f"{arg}.yaml"]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    raise CampaignError(f"브리프 파일을 찾지 못했어요: {arg}")


def read_brief(path: Path) -> dict[str, Any]:
    import yaml  # type: ignore

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:  # type: ignore[attr-defined]
        raise CampaignError(f"브리프 YAML을 읽지 못했어요: {e}") from e
    if not isinstance(data, dict):
        raise CampaignError("브리프는 YAML 매핑(키: 값)이어야 해요.")
    return data


def _as_date(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v).strip())
    except ValueError:
        return None


def _str_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return [str(x) for x in v if str(x).strip()]


def check_brief(brief: dict, cfg: dict, today: date) -> tuple[list[str], list[str]]:
    """(hard, soft). hard가 하나라도 있으면 그래프는 blocked."""
    rv = cfg["review"]
    hard: list[str] = []
    soft: list[str] = []
    cid = str(brief.get("id") or "")
    if not ID_RE.match(cid):
        hard.append("id: 영문 소문자·숫자·하이픈 2~41자 (예: ax-webinar-oct)")
    if not str(brief.get("name") or "").strip():
        hard.append("name: 캠페인 이름이 비어 있어요")
    if brief.get("objective") not in cfg["objectives"]:
        hard.append(f"objective: {', '.join(cfg['objectives'])} 중 하나")
    url = str(brief.get("landing_url") or "")
    u = urlparse(url)
    if u.scheme != "https" or not u.netloc:
        hard.append("landing_url: https:// 로 시작하는 주소여야 해요")
    elif rv.get("allowed_landing_domains"):
        host = u.netloc.lower().split(":")[0]
        if not any(host == d or host.endswith("." + d) for d in rv["allowed_landing_domains"]):
            hard.append(f"landing_url: 허용 도메인({', '.join(rv['allowed_landing_domains'])})이 아니에요")
    if brief.get("cta") not in rv["cta_allowed"]:
        hard.append(f"cta: {', '.join(rv['cta_allowed'])} 중 하나")
    aud = brief.get("audience") or {}
    if not str(aud.get("description") or "").strip():
        hard.append("audience.description: 타깃 설명이 비어 있어요")
    budget = (brief.get("budget") or {}).get("daily_krw")
    if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0:
        hard.append("budget.daily_krw: 양의 정수(원)여야 해요")
    elif budget > int(rv["max_daily_krw"]):
        hard.append(f"budget.daily_krw: ₩{budget:,} — 상한 ₩{int(rv['max_daily_krw']):,} 초과 (오타인지 확인)")
    sch = brief.get("schedule") or {}
    start, end = _as_date(sch.get("start")), _as_date(sch.get("end"))
    if not start or not end:
        hard.append("schedule.start / schedule.end: YYYY-MM-DD")
    elif end < start:
        hard.append("schedule: 종료일이 시작일보다 빨라요")
    elif start < today:
        soft.append(f"schedule.start {start} — 오늘보다 이전이에요. 광고 관리자에서 날짜를 다시 넣으세요")
    for i, c in enumerate(brief.get("substantiated_claims") or [], 1):
        if not isinstance(c, dict) or not str(c.get("claim") or "").strip() or not str(c.get("source") or "").strip():
            hard.append(f"substantiated_claims[{i}]: claim과 source가 모두 있어야 해요")
    if not _str_list(brief.get("keywords")):
        soft.append("keywords: 비어 있으면 리서치 연결(M1·수요 레이더)이 약해져요")
    return hard, soft


# ── research (결정적) ─────────────────────────────────────────────────────
def _tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[\s·,/()\-]+", s.lower()) if len(t) >= 2}


def _latest_brief_file(root: Path) -> Path | None:
    files = sorted(p for p in (root / "content" / "research").glob("*_brief.md") if not p.name.startswith("_"))
    return files[-1] if files else None


def _latest_radar_file(root: Path, cfg: dict, allow_sample: bool) -> Path | None:
    files = sorted(root.glob(cfg["research"]["radar_glob"]))
    real = [p for p in files if not p.name.startswith("_")]
    if real:
        return real[-1]
    if allow_sample:
        sample = [p for p in files if p.name.startswith("_sample_")]
        return sample[-1] if sample else None
    return None


def research(brief: dict, cfg: dict, mode: str) -> dict[str, Any]:
    root = workdir()
    kws = _str_list(brief.get("keywords"))
    kw_tokens = set().union(*(_tokens(k) for k in kws)) if kws else set()
    ctx: dict[str, Any] = {"insights": [], "radar": [], "sources": [], "notes": []}

    bf = _latest_brief_file(root)
    if bf and kws:
        try:
            from lib.content_quality import parse_brief  # lazy — heavy module

            _, insights = parse_brief(bf.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            insights = []
            ctx["notes"].append(f"M1 브리프 파싱 실패: {e}")
        scored = []
        for ins in insights:
            blob = f"{ins.title} {ins.summary} {getattr(ins, 'marketer_view', '')}".lower()
            score = sum(2 for k in kws if k.lower() in blob) + len(kw_tokens & _tokens(blob))
            if score:
                scored.append((score, ins))
        scored.sort(key=lambda x: -x[0])
        seen: set[str] = set()
        uniq = []
        for score, ins in scored:  # 같은 제목·요약이 출처만 바꿔 반복되는 경우 하나만
            key = f"{ins.title}|{ins.summary[:80]}"
            if key not in seen:
                seen.add(key)
                uniq.append((score, ins))
        for score, ins in uniq[: int(cfg["research"]["max_insights"])]:
            ctx["insights"].append({"title": ins.title, "summary": ins.summary[:220], "url": ins.url, "score": score})
            if ins.url:
                ctx["sources"].append({"label": f"M1 {bf.stem}: {ins.title}", "url": ins.url})
    elif not bf:
        ctx["notes"].append("M1 브리프 없음")

    rf = _latest_radar_file(root, cfg, allow_sample=(mode == "sample"))
    if rf:
        text = rf.read_text(encoding="utf-8")
        rising = re.findall(r"^- `/research (.+?)`\s*$", text, re.M)
        hits = [r for r in rising if not kw_tokens or (_tokens(r) & kw_tokens)]
        ctx["radar"] = hits
        src = re.search(r"^## 조건과 출처\s*\n+- (.+)$", text, re.M)
        ctx["sources"].append({"label": f"수요 레이더 {rf.name}", "url": "", "detail": src.group(1) if src else ""})
    else:
        ctx["notes"].append("수요 레이더 리포트 없음")
    return ctx


# ── copy generation ───────────────────────────────────────────────────────
Generator = Callable[[dict, dict, list[dict], int], list[dict]]


def build_copy_prompt(state: dict, cfg: dict, targets: list[dict], out_path: Path) -> str:
    b = state["brief"]
    rv = cfg["review"]
    lim = rv["recommended_length"]
    claims = [f"{c['claim']} (근거: {c['source']})" for c in b.get("substantiated_claims") or []]
    lines = [
        "당신은 한국 B2B 퍼포먼스 마케팅 카피라이터입니다. Meta(페이스북·인스타그램) 광고 카피를 씁니다.",
        "",
        "## 캠페인 브리프",
        f"- 이름: {b.get('name')}",
        f"- 목표: {b.get('objective')}",
        f"- 제안: {(b.get('offer') or {}).get('summary', '')}",
        f"- 제안 조건: {(b.get('offer') or {}).get('conditions', '') or '(없음)'}",
        f"- 타깃: {(b.get('audience') or {}).get('description', '')}",
        f"- 핵심 메시지: {' / '.join(_str_list(b.get('key_messages'))) or '(없음)'}",
        f"- 톤: {b.get('tone') or '전문적이지만 쉬운 해요체'}",
        f"- 반드시 넣을 말: {', '.join(_str_list(b.get('must_include'))) or '(없음)'}",
        f"- 쓰면 안 되는 말: {', '.join(_str_list(b.get('banned_words'))) or '(없음)'}",
        f"- 근거가 있는 표현: {'; '.join(claims) or '(없음)'}",
    ]
    ctx = state.get("context") or {}
    if ctx.get("insights") or ctx.get("radar"):
        lines += ["", "## 참고 신호 (카피에 억지로 넣지 말고 각도를 잡는 데만 쓰세요)"]
        lines += [f"- 트렌드: {i['title']} — {i['summary'][:120]}" for i in ctx.get("insights", [])]
        if ctx.get("radar"):
            lines.append(f"- 최근 검색이 늘어난 키워드: {', '.join(ctx['radar'])}")
    lines += [
        "",
        "## 규칙",
        f"- 본문(primary_text) {lim['primary_text']}자 이하, 제목(headline) {lim['headline']}자 이하, 설명(description) {lim['description']}자 이하",
        f"- 근거 없는 최상급·단정 표현 금지: {', '.join(rv['require_evidence'])} (위 '근거가 있는 표현'만 예외)",
        f"- {', '.join(rv['needs_conditions'])} 같은 말을 쓰면 제안 조건과 어긋나지 않게",
        "- 카피 안에 URL·링크 금지, 자리표시자({{ }}, TODO 등) 금지, 해요체",
        "- 변형마다 각도(angle)를 다르게: 예) 사례·숫자, 문제 제기, 혜택",
    ]
    if targets:
        lines += ["", "## 다시 쓸 변형 (아래 변형만, 같은 id로)"]
        for v in targets:
            issues = (v.get("review") or {}).get("hard", []) + (v.get("review") or {}).get("soft", [])
            lines.append(f"- id {v['id']} ({v.get('angle', '')}): 제목 「{v.get('headline', '')}」 본문 「{v.get('primary_text', '')}」")
            lines.append(f"  고칠 점: {' / '.join(issues)}")
        n_line = f"위 {len(targets)}개 변형만"
    else:
        n_line = f"변형 {int(cfg['copy']['variants'])}개 (id 1부터)"
    lines += [
        "",
        "## 출력",
        f"{n_line}을 아래 JSON 형식으로 이 파일에 저장하세요: {out_path}",
        '{"variants": [{"id": 1, "angle": "...", "primary_text": "...", "headline": "...", "description": "..."}]}',
        "다른 파일은 만들지 말고, 저장한 뒤 'saved' 한 단어만 답하세요.",
    ]
    return "\n".join(lines)


def parse_variants(text: str) -> list[dict]:
    """자유 텍스트에서 {"variants": [...]} JSON을 찾아 정규화."""
    if not text:
        return []
    text = re.sub(r"```(?:json)?", "", text)
    dec = json.JSONDecoder()
    found: Any = None
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("variants"), list):
            found = obj["variants"]  # 마지막 것이 최종 응답
    out = []
    for v in found or []:
        if not isinstance(v, dict):
            continue
        try:
            vid = int(v.get("id"))
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "id": vid,
                "angle": str(v.get("angle") or "").strip(),
                **{f: str(v.get(f) or "").strip() for f in TEXT_FIELDS},
            }
        )
    return out


def _sample_generator(state: dict, cfg: dict, targets: list[dict], round_no: int) -> list[dict]:
    data = json.loads((REPO_ROOT / cfg["copy"]["sample_fixture"]).read_text(encoding="utf-8"))
    rounds = data["rounds"]
    variants = parse_variants(json.dumps({"variants": rounds[min(round_no, len(rounds)) - 1]}, ensure_ascii=False))
    if targets:
        want = {v["id"] for v in targets}
        variants = [v for v in variants if v["id"] in want]
    return variants


def _record_cost(text: str, cid: str) -> None:
    try:
        from lib.harness import append_cost
        from lib.hermes_cost import parse_run_usage

        usage = parse_run_usage(text)
        append_cost(
            {
                "ts": _now(),
                "path": "HERMES_CAMPAIGN_COPY",
                "channel": "campaign",
                "stamp": cid,
                "tokens": int(usage.get("tokens", 0)),
                "usd": float(usage.get("usd", 0.0)),
                "note": "campaign-launch copy · codex",
            }
        )
    except Exception:  # noqa: BLE001 — 비용 기록 실패가 그래프를 막지 않음
        pass


def _codex_generator(state: dict, cfg: dict, targets: list[dict], round_no: int) -> list[dict]:
    try:
        from lib.loop_budget import check_loop_budget

        budget = check_loop_budget()
        if not budget.ok:
            raise CampaignError(f"LLM 예산 한도로 카피 생성을 멈췄어요: {budget.detail}")
    except ImportError:
        pass
    out = _state_dir(cfg) / f"{state['id']}.copy-r{round_no}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    prompt = build_copy_prompt(state, cfg, targets, out)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", prefix="hermes-campaign-", delete=False) as tf:
        log_path = Path(tf.name)
    env = {**os.environ, "HERMES_USE_CODEX": "1", "HERMES_TOOLSETS": "hermes-cli", "HERMES_RUN_LOG": str(log_path)}
    try:
        proc = subprocess.run(
            [str(SCRIPTS / "hermes-run.sh"), prompt, "-t", "hermes-cli"],
            cwd=str(workdir()),
            capture_output=True,
            text=True,
            timeout=int(cfg["copy"]["timeout_sec"]),
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise CampaignError(f"Codex 카피 생성 시간 초과 ({cfg['copy']['timeout_sec']}s)") from e
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    log_path.unlink(missing_ok=True)
    _record_cost("\n".join([proc.stdout or "", proc.stderr or "", log_text]), state["id"])
    file_text = out.read_text(encoding="utf-8") if out.exists() else ""
    variants = parse_variants(file_text) or parse_variants(proc.stdout or "") or parse_variants(log_text)
    if not variants:
        raise CampaignError(f"Codex 응답에서 카피 JSON을 찾지 못했어요 (exit {proc.returncode})")
    return variants


GENERATORS: dict[str, Generator] = {"sample": _sample_generator, "codex": _codex_generator}


# ── review (결정적) ───────────────────────────────────────────────────────
def _claim_terms(brief: dict) -> dict[str, str]:
    return {str(c["claim"]): str(c["source"]) for c in brief.get("substantiated_claims") or [] if isinstance(c, dict)}


def review_variant(v: dict, brief: dict, cfg: dict) -> dict[str, list[str]]:
    rv = cfg["review"]
    hard: list[str] = []
    soft: list[str] = []
    notes: list[str] = []
    if not v.get("primary_text"):
        hard.append("본문이 비어 있어요")
    if not v.get("headline"):
        hard.append("제목이 비어 있어요")
    blob = " ".join(v.get(f, "") for f in TEXT_FIELDS)
    low = blob.lower()
    for ph in rv["placeholders"]:
        if ph.lower() in low:
            hard.append(f"자리표시자 '{ph}'가 남아 있어요")
    if URL_IN_TEXT_RE.search(blob):
        hard.append("카피 안에 링크가 있어요 — 링크는 Link 칸에만")
    stripped = blob
    for ph in rv["allow_phrases"]:
        stripped = stripped.replace(ph, "")
    claims = _claim_terms(brief)
    missing: list[str] = []
    for term in rv["require_evidence"]:
        if term.lower() in stripped.lower():
            src = next((s for c, s in claims.items() if term.lower() in c.lower()), "")
            if src:
                notes.append(f"'{term}' 근거: {src} — 카피 문맥이 근거와 맞는지 확인")
            else:
                missing.append(f"'{term}'")
    if missing:
        hard.append(f"{'·'.join(missing)} — 표시광고법상 실증이 필요한 표현인데 브리프에 근거가 없어요")
    conditions = str((brief.get("offer") or {}).get("conditions") or "").strip()
    for term in rv["needs_conditions"]:
        if term in blob and not conditions:
            hard.append(f"'{term}' — 조건(offer.conditions)이 브리프에 없어요")
    for term in _str_list(brief.get("banned_words")):
        if term.lower() in low:
            hard.append(f"금지어 '{term}'")
    for term in _str_list(brief.get("must_include")):
        if term.lower() not in low:
            hard.append(f"필수 문구 '{term}'가 없어요")
    for f, limit in rv["recommended_length"].items():
        n = len(v.get(f, ""))
        if n > int(limit):
            soft.append(f"{FIELD_KO.get(f, f)} {n}자 (권장 {limit}자 이하 — 넘으면 잘려 보여요)")
    return {"hard": hard, "soft": soft, "notes": notes}


# ── nodes ─────────────────────────────────────────────────────────────────
@dataclass
class Ctx:
    cfg: dict
    today: date
    generator: Generator
    notify: bool
    by: str = "cli"


def _active(state: dict) -> list[dict]:
    return [v for v in state.get("variants", []) if v.get("status") != "dropped"]


def _log(state: dict, node: str, note: str) -> None:
    state.setdefault("history", []).append({"node": node, "at": _now(), "note": note})


def n_load_brief(state: dict, ctx: Ctx) -> None:
    path = Path(state["brief_path"])
    brief = read_brief(path)
    hard, soft = check_brief(brief, ctx.cfg, ctx.today)
    state["brief"] = brief
    state["brief_hash"] = _sha(path.read_text(encoding="utf-8"))
    state["brief_issues"] = {"hard": hard, "soft": soft}
    if hard:
        state["blocked_reason"] = "브리프 확인 필요: " + " · ".join(hard)
    _log(state, "load_brief", f"hard {len(hard)} · soft {len(soft)}")


def n_research(state: dict, ctx: Ctx) -> None:
    state["context"] = research(state["brief"], ctx.cfg, state["mode"])
    c = state["context"]
    _log(state, "research", f"M1 인사이트 {len(c['insights'])} · 레이더 {len(c['radar'])}")


def n_copy(state: dict, ctx: Ctx) -> None:
    round_no = int(state.get("attempts", 0)) + 1
    targets = [v for v in _active(state) if v["review"]["hard"] or v["review"]["soft"]] if round_no > 1 else []
    try:
        new = ctx.generator(state, ctx.cfg, targets, round_no)
    except CampaignError as e:
        state["blocked_reason"] = str(e)
        new = []
    state["attempts"] = round_no
    if round_no == 1:
        ids = [v["id"] for v in new]
        if len(set(ids)) != len(ids):
            state["blocked_reason"] = "카피 변형 id가 겹쳐요"
            new = []
        state["variants"] = [{**v, "round": 1, "status": "draft", "review": {"hard": [], "soft": [], "notes": []}} for v in new]
    else:
        # 걸린 변형만 교체 — 통과한 변형은 모델이 다시 써 보내도 건드리지 않음
        want = {v["id"] for v in targets}
        by_id = {v["id"]: v for v in new if v["id"] in want}
        for v in state["variants"]:
            if v["id"] in by_id:
                v.update({**by_id[v["id"]], "round": round_no})
    _log(state, "copy", f"round {round_no} · {'재작성 ' + str(len(targets)) if targets else '생성 ' + str(len(new))}개")


def n_review(state: dict, ctx: Ctx) -> None:
    seen: dict[str, int] = {}
    for v in _active(state):
        v["review"] = review_variant(v, state["brief"], ctx.cfg)
        key = v.get("headline", "")
        if key and key in seen:
            v["review"]["soft"].append(f"제목이 {seen[key]}번과 같아요")
        seen.setdefault(key, v["id"])
    act = _active(state)
    for v in act:
        if v["review"]["hard"] or v["review"]["soft"]:
            state.setdefault("review_log", []).append(
                {"round": state["attempts"], "id": v["id"], "hard": v["review"]["hard"], "soft": v["review"]["soft"]}
            )
    n_hard = sum(1 for v in act if v["review"]["hard"])
    n_soft = sum(1 for v in act if v["review"]["soft"] and not v["review"]["hard"])
    _log(state, "review", f"round {state['attempts']} · 통과 {len(act) - n_hard - n_soft} · 재작성 필요 {n_soft} · 차단 {n_hard}")


def content_hash(state: dict) -> str:
    ready = [{k: v.get(k) for k in ("id", "angle", *TEXT_FIELDS)} for v in state["variants"] if v.get("status") == "ready"]
    return _sha(state["brief_hash"], json.dumps(ready, ensure_ascii=False, sort_keys=True))


def n_approval(state: dict, ctx: Ctx) -> None:
    for v in state["variants"]:
        if v.get("status") == "dropped":
            continue
        v["status"] = "dropped" if v["review"]["hard"] else "ready"
    state["status"] = "awaiting_approval"
    state["approval"] = {"requested_at": _now(), "content_hash": content_hash(state)}
    card = format_approval_card(state, ctx.cfg)
    p = _state_dir(ctx.cfg) / f"{state['id']}.approval.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(card + "\n", encoding="utf-8")
    state["approval"]["card_path"] = str(p)
    _log(state, "approval", f"승인 대기 · 변형 {sum(1 for v in state['variants'] if v['status'] == 'ready')}개")
    if ctx.notify:
        notify(card)


def _names(state: dict) -> dict[str, str]:
    b = state["brief"]
    label = str((b.get("audience") or {}).get("label") or "main")
    return {"campaign": str(b["name"]), "adset": f"{b['name']}_{label}"}


def _url_tags(cfg: dict, cid: str, vid: int) -> str:
    utm = cfg["package"]["utm"]
    return urlencode(
        {"utm_source": utm.get("source", "meta"), "utm_medium": utm.get("medium", "paid_social"), "utm_campaign": cid, "utm_content": f"v{vid}"}
    )


def output_paths(state: dict, cfg: dict, stamp: str) -> dict[str, Path]:
    prefix = "_sample_" if state["mode"] == "sample" else ""
    base = workdir() / cfg["outputs_dir"] / f"{prefix}{stamp}_campaign_{state['id']}"
    return {"launch": Path(f"{base}_launch.md"), "csv": Path(f"{base}_ads.csv")}


def build_ads_csv(state: dict, cfg: dict) -> str:
    cols = cfg["package"]["columns"]
    order = ["campaign_name", "adset_name", "ad_name", "ad_status", "headline", "primary_text", "description", "link", "cta", "url_tags"]
    order = [k for k in order if k in cols]
    names = _names(state)
    b = state["brief"]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([cols[k] for k in order])
    for v in _picked(state):
        row = {
            "campaign_name": names["campaign"],
            "adset_name": names["adset"],
            "ad_name": f"{state['id']}_v{v['id']}",
            "ad_status": cfg["package"]["status"],
            "headline": v["headline"],
            "primary_text": v["primary_text"],
            "description": v.get("description", ""),
            "link": b["landing_url"],
            "cta": b["cta"],
            "url_tags": _url_tags(cfg, state["id"], v["id"]),
        }
        w.writerow([row[k] for k in order])
    return buf.getvalue()


def _picked(state: dict) -> list[dict]:
    picks = set((state.get("approval") or {}).get("picks") or [])
    return [v for v in state["variants"] if v.get("status") == "ready" and (not picks or v["id"] in picks)]


def build_launch_md(state: dict, cfg: dict, paths: dict[str, Path]) -> str:
    b = state["brief"]
    a = state["approval"]
    names = _names(state)
    sch = b.get("schedule") or {}
    aud = b.get("audience") or {}
    lim = cfg["review"]["recommended_length"]
    out = [f"# 캠페인 런칭 패키지 · {b['name']}", ""]
    if state["mode"] == "sample":
        out += ["> 샘플 카피로 만든 패키지입니다. 실제 집행용이 아닙니다.", ""]
    out += [
        f"- 캠페인 id: `{state['id']}` · 승인: {_kst(a.get('approved_at', ''))} · {a.get('approved_by', '')}",
        f"- 승인한 변형: {', '.join(str(v['id']) for v in _picked(state))}",
        "- 광고 계정에는 아무것도 올리지 않았어요. 아래 순서대로 사람이 광고 관리자에서 올립니다.",
        "",
        "## 1. 광고 관리자에서 직접 넣을 값 (CSV에 없음)",
        "",
        "| 항목 | 값 |",
        "| --- | --- |",
        f"| 캠페인 이름 | {names['campaign']} |",
        f"| 캠페인 목표 | {cfg['objectives'].get(b['objective'], b['objective'])} |",
        f"| 광고세트 이름 | {names['adset']} |",
        f"| 일 예산 | ₩{int(b['budget']['daily_krw']):,} |",
        f"| 기간 | {sch.get('start')} ~ {sch.get('end')} |",
        f"| 타깃 | {aud.get('description', '')} |",
        f"| 타깃 메모 | {aud.get('notes', '') or '—'} |",
        f"| 행동 유도 버튼 | {b['cta']} |",
        f"| 랜딩 | {b['landing_url']} |",
        "",
        "## 2. 승인된 카피",
        "",
        f"| # | 각도 | 제목 (≤{lim['headline']}) | 본문 (≤{lim['primary_text']}) | 설명 (≤{lim['description']}) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for v in _picked(state):
        cells = [str(v["id"]), v.get("angle", "")] + [f"{v.get(f, '')} ({len(v.get(f, ''))}자)" for f in ("headline", "primary_text", "description")]
        out.append("| " + " | ".join(c.replace("|", "／").replace("\n", " ") for c in cells) + " |")
    warns = [f"- #{v['id']}: {s}" for v in _picked(state) for s in v["review"]["soft"]]
    notes = [f"- #{v['id']}: {s}" for v in _picked(state) for s in v["review"].get("notes", [])]
    if warns:
        out += ["", "권장치를 넘은 항목 (승인 시 확인됨):", "", *warns]
    if notes:
        out += ["", "근거 표현 — 게재 전 문맥 확인:", "", *notes]
    out += ["", "## 3. 링크·UTM", "", "| # | URL Tags |", "| --- | --- |"]
    out += [f"| {v['id']} | `{_url_tags(cfg, state['id'], v['id'])}` |" for v in _picked(state)]
    out += [
        "",
        "## 4. 올리는 순서",
        "",
        "1. 광고 관리자에서 캠페인·광고세트를 만들고 1번 값을 넣습니다. 켜지 말고 둡니다.",
        f"2. 그 광고세트에 광고 1개를 임시로 만든 뒤 내보내기(export)해서 `{paths['csv'].name}`의 열 이름과 비교합니다. "
        "다르면 `config/campaign-launch.yaml`의 `package.columns`를 고치고 `campaign-launch.py repackage "
        f"{state['id']}`로 다시 만듭니다.",
        f"3. `{paths['csv'].name}`을 가져오기(import)합니다. 모든 광고가 `{cfg['package']['status']}` 상태로 들어옵니다.",
        "4. 광고마다 이미지·영상을 연결하고 미리보기를 봅니다.",
        "5. 아래 확인을 마친 뒤 직접 켭니다.",
        "",
        "## 5. 켜기 전 확인",
        "",
        "- [ ] 이미지·영상 안 문구가 승인된 카피와 같은 약속을 하는지",
        "- [ ] 개인 특성(나이·건강·재정 상태 등)을 단정하거나 암시하는 표현이 없는지 (Meta 광고 정책)",
        "- [ ] 랜딩 페이지의 조건(무료·마감·인원)이 광고와 같은지",
        "- [ ] 전환 목표라면 픽셀·전환 이벤트가 연결됐는지",
        "- [ ] 특별 광고 카테고리(고용·주택·금융 등) 해당 여부",
        "",
        "## 6. 게재 후 감시 (인계)",
        "",
        f"- 광고세트 이름 `{names['adset']}` 그대로 쓰면 meta-fatigue 루프(매일 09:00, `config/meta-ads.yaml`)가 "
        "빈도·CTR 변화로 교체 검토 알림을 보내고, 월요일 주간 리포트에 포함됩니다.",
        "- 이 패키지는 예산·입찰·상태를 바꾸지 않습니다. 교체·증액은 광고 관리자에서 사람이 합니다.",
        "",
        "## 7. 출처·조건",
        "",
        f"- 브리프: `{Path(state['brief_path']).name}` (sha256 {state['brief_hash'][:12]})",
        f"- 카피: {'샘플 픽스처' if state['mode'] == 'sample' else 'Codex (hermes-run.sh, HERMES_USE_CODEX=1)'} · 검수 {state['attempts']}회차",
        "- 검수 규칙: `config/campaign-launch.yaml` review (Meta 권장 글자 수 · 표시광고법 실증 필요 표현 · 조건 표기)",
    ]
    ctx_ = state.get("context") or {}
    for s in ctx_.get("sources", []):
        tail = s.get("url") or s.get("detail") or ""
        out.append(f"- 리서치: {s['label']}" + (f" — {tail}" if tail else ""))
    out += [f"- 리서치: {n}" for n in ctx_.get("notes", [])]
    fixed = [r for r in state.get("review_log", []) if r["round"] < state["attempts"]]
    if fixed:
        out += ["", "검수 이력 (재작성으로 고친 것):", ""]
        out += [f"- {r['round']}회차 #{r['id']}: " + " / ".join(r["hard"] + r["soft"]) for r in fixed]
    return "\n".join(out) + "\n"


def n_package(state: dict, ctx: Ctx) -> None:
    stamp = ctx.today.isoformat()
    paths = output_paths(state, ctx.cfg, stamp)
    paths["launch"].parent.mkdir(parents=True, exist_ok=True)
    paths["csv"].write_text(build_ads_csv(state, ctx.cfg), encoding="utf-8-sig")
    paths["launch"].write_text(build_launch_md(state, ctx.cfg, paths), encoding="utf-8")
    state["package"] = {k: str(p) for k, p in paths.items()}
    state["package"]["built_at"] = _now()
    _log(state, "package", f"{paths['launch'].name} · {paths['csv'].name}")


def n_handoff(state: dict, ctx: Ctx) -> None:
    names = _names(state)
    state["handoff"] = {"meta_fatigue": {"campaign_name": names["campaign"], "adset_name": names["adset"]}}
    state["status"] = "packaged"
    _log(state, "handoff", f"meta-fatigue 감시 대상: {names['adset']}")
    if ctx.notify:
        notify(
            f"📦 캠페인 런칭 패키지 준비 · {state['brief']['name']} ({state['id']})\n"
            f"{Path(state['package']['launch']).name}\n{Path(state['package']['csv']).name}\n"
            "광고 관리자에 올리고 켜는 건 사람이 합니다 (모든 광고 일시중지 상태)."
        )


NODES: dict[str, Callable[[dict, Ctx], None]] = {
    "load_brief": n_load_brief,
    "research": n_research,
    "copy": n_copy,
    "review": n_review,
    "approval": n_approval,
    "package": n_package,
    "handoff": n_handoff,
}


def _route(node: str, state: dict, cfg: dict) -> str:
    if node == "load_brief":
        return "blocked" if state["brief_issues"]["hard"] else "research"
    if node == "research":
        return "copy"
    if node == "copy":
        if state.get("blocked_reason") or not _active(state):
            state.setdefault("blocked_reason", "카피가 만들어지지 않았어요")
            return "blocked"
        return "review"
    if node == "review":
        act = _active(state)
        failing = [v for v in act if v["review"]["hard"] or v["review"]["soft"]]
        need = int(cfg["copy"]["min_passing"])
        if failing and int(state["attempts"]) <= int(cfg["copy"]["max_retries"]):
            return "copy"
        ready = [v for v in act if not v["review"]["hard"]]
        if len(ready) >= need:
            return "approval"
        state["blocked_reason"] = (
            f"통과한 변형이 {len(ready)}개 (필요 {need}개)"
            + (f" — 재작성 {cfg['copy']['max_retries']}회 뒤" if failing else "")
        )
        return "blocked"
    return GRAPH[node][0]


def run_graph(state: dict, ctx: Ctx, start: str) -> dict:
    node = start
    path = []
    while node not in STOP:
        if node not in NODES:
            raise CampaignError(f"알 수 없는 노드: {node}")
        NODES[node](state, ctx)
        nxt = _route(node, state, ctx.cfg)
        if nxt not in GRAPH[node]:
            raise CampaignError(f"그래프에 없는 간선: {node} → {nxt}")
        path.append(node)
        save_state(ctx.cfg, state)
        node = nxt
    if node == "blocked":
        state["status"] = "blocked"
        _log(state, "blocked", state.get("blocked_reason", ""))
        save_state(ctx.cfg, state)
        if ctx.notify:
            notify(f"⛔ 캠페인 그래프 멈춤 · {state['id']}\n{state.get('blocked_reason', '')}")
    state.setdefault("paths", []).append(path + [node])
    save_state(ctx.cfg, state)
    return state


# ── public API ────────────────────────────────────────────────────────────
def _want_notify(cfg: dict, mode: str, override: bool | None) -> bool:
    if os.environ.get("HERMES_CAMPAIGN_NOTIFY") == "0":
        return False
    if override is not None:
        return override
    setting = str(cfg.get("notify", "auto"))
    return setting == "always" or (setting == "auto" and mode == "codex")


def start_campaign(
    brief_arg: str,
    *,
    cfg: dict | None = None,
    mode: str | None = None,
    today: date | None = None,
    generator: Generator | None = None,
    notify_override: bool | None = None,
    restart: bool = False,
) -> dict:
    cfg = cfg or load_config()
    mode = mode or cfg["mode"]
    if mode not in GENERATORS and generator is None:
        raise CampaignError(f"mode는 {', '.join(GENERATORS)} 중 하나예요")
    path = resolve_brief_path(cfg, brief_arg)
    cid = str(read_brief(path).get("id") or "")
    if ID_RE.match(cid) and _state_path(cfg, cid).exists():
        prev = load_state(cfg, cid)
        if prev.get("status") in ("approved", "packaged") and not restart:
            raise CampaignError(f"'{cid}'은 이미 {STATUS_KO[prev['status']]} 상태예요. 새 id로 브리프를 만들거나 --restart를 쓰세요.")
    state: dict[str, Any] = {
        "id": cid if ID_RE.match(cid) else f"invalid-{_sha(str(path))[:8]}",
        "brief_path": str(path),
        "mode": mode,
        "status": "running",
        "attempts": 0,
        "variants": [],
        "created_at": _now(),
    }
    ctx = Ctx(
        cfg=cfg,
        today=today or date.today(),
        generator=generator or GENERATORS[mode],
        notify=_want_notify(cfg, mode, notify_override),
    )
    return run_graph(state, ctx, "load_brief")


def approve(
    cid: str,
    picks: list[int] | None = None,
    *,
    cfg: dict | None = None,
    by: str = "cli",
    today: date | None = None,
    notify_override: bool | None = None,
) -> dict:
    cfg = cfg or load_config()
    state = load_state(cfg, cid)
    if state.get("status") != "awaiting_approval":
        raise CampaignError(f"'{cid}'은 승인 대기 상태가 아니에요 (현재: {STATUS_KO.get(state.get('status'), state.get('status'))})")
    path = Path(state["brief_path"])
    if not path.exists() or _sha(path.read_text(encoding="utf-8")) != state["brief_hash"]:
        raise CampaignError("승인 요청 뒤 브리프 파일이 바뀌었어요. `campaign-launch.py run`으로 다시 돌려 새 승인 카드를 받으세요.")
    if content_hash(state) != state["approval"]["content_hash"]:
        raise CampaignError("승인 요청 뒤 카피가 바뀌었어요. 다시 돌려 새 승인 카드를 받으세요.")
    ready = [v["id"] for v in state["variants"] if v.get("status") == "ready"]
    picks = sorted(set(picks or []))
    bad = [p for p in picks if p not in ready]
    if bad:
        raise CampaignError(f"승인할 수 없는 변형 번호: {bad} (가능: {ready})")
    state["approval"].update({"approved_at": _now(), "approved_by": by, "picks": picks})
    state["status"] = "approved"
    _log(state, "human", f"승인 · {by} · 변형 {picks or ready}")
    ctx = Ctx(cfg=cfg, today=today or date.today(), generator=GENERATORS["sample"], notify=_want_notify(cfg, state["mode"], notify_override), by=by)
    return run_graph(state, ctx, "package")


def repackage(cid: str, *, cfg: dict | None = None, today: date | None = None) -> dict:
    """열 이름을 고친 뒤 같은 승인본으로 패키지만 다시 만듦 (승인 내용은 그대로)."""
    cfg = cfg or load_config()
    state = load_state(cfg, cid)
    if state.get("status") != "packaged":
        raise CampaignError("패키지 완료 상태에서만 다시 만들 수 있어요")
    if content_hash(state) != state["approval"]["content_hash"]:
        raise CampaignError("승인본과 카피가 달라요. 다시 돌려 승인을 받으세요.")
    ctx = Ctx(cfg=cfg, today=today or date.today(), generator=GENERATORS["sample"], notify=False)
    n_package(state, ctx)
    save_state(cfg, state)
    return state


def reject(cid: str, reason: str, *, cfg: dict | None = None, by: str = "cli") -> dict:
    cfg = cfg or load_config()
    state = load_state(cfg, cid)
    if state.get("status") != "awaiting_approval":
        raise CampaignError(f"'{cid}'은 승인 대기 상태가 아니에요")
    state["status"] = "rejected"
    state["rejection"] = {"at": _now(), "by": by, "reason": reason}
    _log(state, "human", f"반려 · {by} · {reason}")
    save_state(cfg, state)
    return state


def notify(msg: str) -> None:
    subprocess.run(["bash", str(SCRIPTS / "lib" / "commander_notify.sh"), "notify", msg], check=False, cwd=str(workdir()))


# ── formatting ────────────────────────────────────────────────────────────
def format_approval_card(state: dict, cfg: dict) -> str:
    b = state["brief"]
    sch = b.get("schedule") or {}
    ready = [v for v in state["variants"] if v.get("status") == "ready"]
    dropped = [v for v in state["variants"] if v.get("status") == "dropped"]
    head = "[샘플] " if state["mode"] == "sample" else ""
    lines = [
        f"{head}🛡 캠페인 승인 대기 · {b['name']} ({state['id']})",
        f"목표 {cfg['objectives'].get(b['objective'], b['objective'])} · 일 예산 ₩{int(b['budget']['daily_krw']):,} · {sch.get('start')}~{sch.get('end')}",
        f"랜딩 {b['landing_url']} · 버튼 {b['cta']}",
        f"타깃 {(b.get('audience') or {}).get('description', '')}",
        "",
        f"카피 {len(ready)}개 (검수 {state['attempts']}회차)",
    ]
    for v in ready:
        lines += ["", f"[{v['id']}] {v.get('angle', '')}", f"제목: {v['headline']}", f"본문: {v['primary_text']}"]
        if v.get("description"):
            lines.append(f"설명: {v['description']}")
        lines += [f"⚠️ {s}" for s in v["review"]["soft"]]
        lines += [f"🔎 {s}" for s in v["review"].get("notes", [])]
    fixed = [r for r in state.get("review_log", []) if r["round"] < state["attempts"]]
    if fixed:
        lines += ["", "검수에서 고친 것:"]
        lines += [f"- {r['round']}회차 [{r['id']}] " + " / ".join(r["hard"] + r["soft"]) for r in fixed]
    if dropped:
        lines += ["", "제외된 변형: " + ", ".join(f"[{v['id']}] {v['review']['hard'][0]}" for v in dropped)]
    for s in state.get("brief_issues", {}).get("soft", []):
        lines.append(f"ℹ️ {s}")
    lines += [
        "",
        "사람이 볼 것: 이미지·랜딩 문구, 개인 특성 암시 표현",
        "",
        f"승인: 캠페인 승인 {state['id']}",
        f"일부만: 캠페인 승인 {state['id']} {' '.join(str(v['id']) for v in ready[:2])}",
        f"반려: 캠페인 반려 {state['id']} <사유>",
        "※ 일반 메시지로 보내 주세요. 슬래시 /approve는 뒤 글자가 전달되지 않아 대기 목록만 보여줘요.",
        "승인해도 광고 계정에는 아무것도 올라가지 않아요. 런칭 패키지 파일만 만들어요.",
    ]
    return "\n".join(lines)


def format_status(state: dict) -> str:
    st = STATUS_KO.get(state.get("status"), state.get("status"))
    name = (state.get("brief") or {}).get("name", "")
    lines = [f"• {state['id']} — {name} · {st} · 검수 {state.get('attempts', 0)}회차"]
    if state.get("status") == "blocked":
        lines.append(f"  이유: {state.get('blocked_reason', '')}")
    if state.get("status") == "packaged":
        lines.append(f"  패키지: {Path(state['package']['launch']).name}")
    if state.get("status") == "rejected":
        lines.append(f"  반려 사유: {state['rejection']['reason']}")
    return "\n".join(lines)


def format_pending(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    waiting = [s for s in list_states(cfg) if s.get("status") == "awaiting_approval"]
    if not waiting:
        return ""
    lines = ["📣 캠페인 승인 대기", ""]
    for s in waiting:
        n = sum(1 for v in s["variants"] if v.get("status") == "ready")
        lines.append(f"• {s['id']} — {s['brief']['name']} · 카피 {n}개 · 요청 {s['approval']['requested_at'][:10]}")
    lines += ["", "카드 다시 보기: 캠페인 목록 · 승인: 캠페인 승인 <id>"]
    return "\n".join(lines)


def format_list(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    states = list_states(cfg)
    if not states:
        return "📭 캠페인 없음 — 브리프: campaign-launch.py new <id>"
    lines = ["📣 캠페인", ""]
    lines += [format_status(s) for s in states]
    return "\n".join(lines)


def brief_template(cid: str) -> str:
    if not ID_RE.match(cid):
        raise CampaignError(f"캠페인 id 형식이 아니에요: {cid!r} (영문 소문자·숫자·하이픈)")
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    return re.sub(r"^id: .*$", f"id: {cid}", text, count=1, flags=re.M)
