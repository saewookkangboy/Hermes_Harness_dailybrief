"""뉴스레터 CTOR 실측 — 기록·집계·대시보드."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.common import read_template, truncate
from lib.newsletter_quality import load_newsletter_config

WORKDIR = Path(__file__).resolve().parents[2]
METRICS_PATH = WORKDIR / ".harness" / "newsletter-ctor-metrics.json"
TEMPLATE_PATH = WORKDIR / "templates" / "dashboard" / "newsletter-ctor.html"
REPORT_DIR = WORKDIR / "content" / "logs"


def _parse_pct_range(raw: str, default_lo: float, default_hi: float) -> tuple[float, float]:
    nums = [float(x) for x in re.findall(r"[\d.]+", str(raw or ""))]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], default_hi
    return default_lo, default_hi


def _ctor_targets(cfg: dict | None = None) -> tuple[float, float, float, float]:
    c = cfg or load_newsletter_config()
    b = c.get("benchmarks") or {}
    lo, hi = _parse_pct_range(b.get("ctor_target", "10-15%"), 10.0, 15.0)
    o_lo, o_hi = _parse_pct_range(b.get("open_rate_b2b", "18-25%"), 18.0, 25.0)
    return lo, hi, o_lo, o_hi


def learning_config(cfg: dict | None = None) -> dict[str, Any]:
    c = cfg or load_newsletter_config()
    return c.get("learning") or {}


def seed_markers(cfg: dict | None = None) -> list[str]:
    marks = learning_config(cfg).get("seed_markers") or ["p4-eval-seed", "seed:true"]
    return [str(m).lower() for m in marks if m]


def is_seed_record(row: dict[str, Any], cfg: dict | None = None) -> bool:
    """평가용 시드 판별 — 실측 학습에서 제외 (R27)."""
    if row.get("seed") is True:
        return True
    notes = str(row.get("notes") or "").lower()
    return any(marker in notes for marker in seed_markers(cfg))


def secondary_targets(cfg: dict | None = None) -> dict[str, float]:
    t = (learning_config(cfg).get("targets") or {})
    return {
        "ctor_min_pct": float(t.get("ctor_min_pct", 10.0)),
        "ctr_min_pct": float(t.get("ctr_min_pct", 2.0)),
        "ctr_max_pct": float(t.get("ctr_max_pct", 3.0)),
        "reply_min_pct": float(t.get("reply_min_pct", 1.0)),
        "unsub_max_pct": float(t.get("unsub_max_pct", 0.5)),
    }


def _pattern_id_for(stamp: str) -> str:
    """발행 원장에서 해당 호의 제목 패턴 조회 (R26)."""
    try:
        from lib.newsletter_issue_ledger import read_ledger

        for row in read_ledger(limit=90):
            if row.get("stamp") == stamp:
                return str(row.get("pattern_id") or "")
    except (ImportError, OSError):
        pass
    return ""


def _health_flags(
    *,
    ctor: float,
    ctr: float,
    reply_rate: float,
    unsub_rate: float,
    cfg: dict | None = None,
) -> list[str]:
    """CTOR 외 보조 지표 상태 — 오픈율은 MPP 영향으로 방향성만 (R24, R25)."""
    t = secondary_targets(cfg)
    flags: list[str] = []
    flags.append("ctor_ok" if ctor >= t["ctor_min_pct"] else "ctor_low")
    if ctr < t["ctr_min_pct"]:
        flags.append("ctr_low")
    elif ctr > t["ctr_max_pct"]:
        flags.append("ctr_high")
    else:
        flags.append("ctr_ok")
    if reply_rate:
        flags.append("reply_ok" if reply_rate >= t["reply_min_pct"] else "reply_low")
    if unsub_rate:
        flags.append("unsub_ok" if unsub_rate < t["unsub_max_pct"] else "unsub_high")
    return flags


def load_metrics() -> dict[str, Any]:
    if not METRICS_PATH.exists():
        return {"version": 1, "records": []}
    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "records": []}


def save_metrics(data: dict[str, Any]) -> Path:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return METRICS_PATH


def _winner_subject(stamp: str) -> str:
    path = WORKDIR / "content" / "newsletter" / f"{stamp}_newsletter_subject-scores.json"
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return str((data.get("winner") or {}).get("text") or "")
    except (json.JSONDecodeError, OSError):
        return ""


def record_campaign(
    stamp: str,
    *,
    delivered: int,
    unique_opens: int,
    unique_clicks: int,
    subject: str = "",
    notes: str = "",
    replies: int = 0,
    unsubscribes: int = 0,
    pattern_id: str = "",
    seed: bool | None = None,
) -> dict[str, Any]:
    if delivered <= 0:
        raise ValueError("delivered must be > 0")
    open_rate = round((unique_opens / delivered) * 100, 2)
    ctor = round((unique_clicks / unique_opens) * 100, 2) if unique_opens else 0.0
    ctr = round((unique_clicks / delivered) * 100, 2)
    reply_rate = round((replies / delivered) * 100, 2)
    unsub_rate = round((unsubscribes / delivered) * 100, 2)
    lo, hi, _, _ = _ctor_targets()
    health = "healthy" if lo <= ctor <= hi else "watch"
    row = {
        "stamp": stamp,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subject": subject or _winner_subject(stamp),
        "pattern_id": pattern_id or _pattern_id_for(stamp),
        "delivered": delivered,
        "unique_opens": unique_opens,
        "unique_clicks": unique_clicks,
        "replies": replies,
        "unsubscribes": unsubscribes,
        "open_rate_pct": open_rate,
        "ctor_pct": ctor,
        "ctr_pct": ctr,
        "reply_rate_pct": reply_rate,
        "unsub_rate_pct": unsub_rate,
        "ctor_health": health,
        "notes": notes,
    }
    row["health_flags"] = _health_flags(
        ctor=ctor, ctr=ctr, reply_rate=reply_rate, unsub_rate=unsub_rate
    )
    row["seed"] = is_seed_record(row) if seed is None else bool(seed)
    data = load_metrics()
    records = [r for r in data.get("records", []) if r.get("stamp") != stamp]
    records.append(row)
    records.sort(key=lambda r: r.get("stamp", ""), reverse=True)
    data["records"] = records
    save_metrics(data)
    try:
        from lib.m4_channel_metrics import sync_ctor_to_channel_metrics

        sync_ctor_to_channel_metrics()
    except ImportError:
        pass
    try:
        from lib.newsletter_ctor_feedback import compute_ctor_feedback

        compute_ctor_feedback()
    except ImportError:
        pass
    return row


def list_records(limit: int = 30, *, include_seed: bool = True) -> list[dict[str, Any]]:
    rows = list(load_metrics().get("records") or [])
    if not include_seed:
        rows = [r for r in rows if not is_seed_record(r)]
    return rows[:limit]


def real_records(limit: int = 30) -> list[dict[str, Any]]:
    """평가 시드를 제외한 실측 기록만 (R27)."""
    return list_records(limit, include_seed=False)


def build_dashboard_md(records: list[dict[str, Any]] | None = None) -> str:
    rows = records if records is not None else list_records()
    lo, hi, o_lo, o_hi = _ctor_targets()
    t = secondary_targets()
    seeds = [r for r in rows if is_seed_record(r)]
    lines = [
        "# Newsletter CTOR Dashboard",
        "",
        f"**CTOR 목표:** {lo}–{hi}% · **Open (방향성, MPP 보정):** {o_lo}–{o_hi}%",
        f"**보조 목표:** CTR {t['ctr_min_pct']}–{t['ctr_max_pct']}% · "
        f"회신 ≥{t['reply_min_pct']}% · 해지 <{t['unsub_max_pct']}%",
        f"**실측 {len(rows) - len(seeds)}건 · 평가 시드 {len(seeds)}건(학습 제외)**",
        f"**갱신:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| 발송일 | 제목 | 패턴 | Delivered | Opens | Clicks | Open% | CTOR% | CTR% | 회신% | 해지% | 상태 |",
        "|--------|------|------|----------:|------:|-------:|------:|------:|-----:|------:|------:|------|",
    ]
    for r in rows:
        subj = truncate(r.get("subject") or "—", 36)
        health = "✅" if r.get("ctor_health") == "healthy" else "⚠️"
        if is_seed_record(r):
            health = f"{health} 시드"
        lines.append(
            f"| {r.get('stamp')} | {subj} | {r.get('pattern_id') or '—'} | {r.get('delivered')} | "
            f"{r.get('unique_opens')} | {r.get('unique_clicks')} | {r.get('open_rate_pct')} | "
            f"{r.get('ctor_pct')} | {r.get('ctr_pct', '—')} | {r.get('reply_rate_pct', '—')} | "
            f"{r.get('unsub_rate_pct', '—')} | {health} |"
        )
    if not rows:
        lines.append("| — | 데이터 없음 | — | — | — | — | — | — | — | — | — | — |")
    lines.extend(
        [
            "",
            "## 기록 방법",
            "```bash",
            "scripts/newsletter-ctor-record.sh YYYY-MM-DD --delivered N --opens N --clicks N \\",
            "  [--replies N] [--unsub N] [--seed]",
            "scripts/newsletter-ctor-dashboard.sh",
            "```",
            "",
            "> 평가용 시드(`--seed`)는 제목 가중치 학습에서 제외됩니다.",
        ]
    )
    return "\n".join(lines)


def build_dashboard_html(records: list[dict[str, Any]] | None = None) -> str:
    rows = records if records is not None else list_records()
    lo, hi, o_lo, o_hi = _ctor_targets()
    t = secondary_targets()
    tpl = read_template("templates/dashboard/newsletter-ctor.html")
    tr_html = ""
    seed_count = 0
    for r in rows:
        badge = "ok" if r.get("ctor_health") == "healthy" else "warn"
        seed = is_seed_record(r)
        seed_count += 1 if seed else 0
        label = truncate(r.get("subject") or "—", 48)
        if seed:
            label = f"{label} <span class='badge warn'>시드</span>"
        tr_html += (
            f"<tr><td>{r.get('stamp')}</td>"
            f"<td>{label}</td>"
            f"<td>{r.get('pattern_id') or '—'}</td>"
            f"<td class='num'>{r.get('delivered')}</td>"
            f"<td class='num'>{r.get('unique_opens')}</td>"
            f"<td class='num'>{r.get('unique_clicks')}</td>"
            f"<td class='num'>{r.get('open_rate_pct')}%</td>"
            f"<td class='num'><span class='badge {badge}'>{r.get('ctor_pct')}%</span></td>"
            f"<td class='num'>{r.get('ctr_pct', '—')}</td>"
            f"<td class='num'>{r.get('reply_rate_pct', '—')}</td>"
            f"<td class='num'>{r.get('unsub_rate_pct', '—')}</td></tr>\n"
        )
    if not tr_html:
        tr_html = "<tr><td colspan='11'>실측 데이터 없음 — newsletter-ctor-record.sh 로 기록</td></tr>"
    latest = rows[0] if rows else {}
    summary = (
        f"최근 호 CTOR {latest.get('ctor_pct', '—')}% · Open {latest.get('open_rate_pct', '—')}%"
        if latest
        else "실측 캠페인 없음"
    )
    return (
        tpl.replace("{{CTOR_TARGET}}", f"{lo}–{hi}%")
        .replace("{{OPEN_TARGET}}", f"{o_lo}–{o_hi}%")
        .replace(
            "{{SECONDARY_TARGET}}",
            f"CTR {t['ctr_min_pct']}–{t['ctr_max_pct']}% · 해지 &lt;{t['unsub_max_pct']}%",
        )
        .replace("{{LEARNING_SAMPLE}}", f"실측 {len(rows) - seed_count} · 시드 {seed_count}")
        .replace("{{SUMMARY}}", summary)
        .replace("{{ROWS}}", tr_html)
        .replace("{{UPDATED}}", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    )


def write_dashboard_outputs(stamp: str | None = None) -> tuple[Path, Path]:
    records = list_records()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    tag = stamp or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md_path = REPORT_DIR / f"{tag}_newsletter-ctor-dashboard.md"
    html_path = REPORT_DIR / f"{tag}_newsletter-ctor-dashboard.html"
    md_path.write_text(build_dashboard_md(records), encoding="utf-8")
    html_path.write_text(build_dashboard_html(records), encoding="utf-8")
    return md_path, html_path


def ctor_summary_for_m4() -> dict[str, Any]:
    records = list_records()
    if not records:
        return {"count": 0, "real_count": 0, "seed_count": 0}
    real = [r for r in records if not is_seed_record(r)]
    healthy = sum(1 for r in records if r.get("ctor_health") == "healthy")
    avg_ctor = round(sum(float(r.get("ctor_pct") or 0) for r in records) / len(records), 2)
    summary = {
        "count": len(records),
        "real_count": len(real),
        "seed_count": len(records) - len(real),
        "healthy_count": healthy,
        "avg_ctor_pct": avg_ctor,
        "latest": records[0],
    }
    if real:
        summary["avg_ctor_pct_real"] = round(
            sum(float(r.get("ctor_pct") or 0) for r in real) / len(real), 2
        )
    return summary
