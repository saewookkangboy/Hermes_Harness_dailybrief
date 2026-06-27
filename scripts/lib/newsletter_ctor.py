"""뉴스레터 CTOR 실측 — 기록·집계·대시보드."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.common import read_template, truncate
from lib.newsletter_quality import load_newsletter_config

WORKDIR = Path.home() / "hermes-content-studio"
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
) -> dict[str, Any]:
    if delivered <= 0:
        raise ValueError("delivered must be > 0")
    open_rate = round((unique_opens / delivered) * 100, 2)
    ctor = round((unique_clicks / unique_opens) * 100, 2) if unique_opens else 0.0
    lo, hi, _, _ = _ctor_targets()
    health = "healthy" if lo <= ctor <= hi else "watch"
    row = {
        "stamp": stamp,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subject": subject or _winner_subject(stamp),
        "delivered": delivered,
        "unique_opens": unique_opens,
        "unique_clicks": unique_clicks,
        "open_rate_pct": open_rate,
        "ctor_pct": ctor,
        "ctor_health": health,
        "notes": notes,
    }
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


def list_records(limit: int = 30) -> list[dict[str, Any]]:
    return list(load_metrics().get("records") or [])[:limit]


def build_dashboard_md(records: list[dict[str, Any]] | None = None) -> str:
    rows = records if records is not None else list_records()
    lo, hi, o_lo, o_hi = _ctor_targets()
    lines = [
        "# Newsletter CTOR Dashboard",
        "",
        f"**CTOR 목표:** {lo}–{hi}% · **Open (방향성):** {o_lo}–{o_hi}%",
        f"**갱신:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| 발송일 | 제목 | Delivered | Opens | Clicks | Open% | CTOR% | 상태 |",
        "|--------|------|----------:|------:|-------:|------:|------:|------|",
    ]
    for r in rows:
        subj = truncate(r.get("subject") or "—", 36)
        health = "✅" if r.get("ctor_health") == "healthy" else "⚠️"
        lines.append(
            f"| {r.get('stamp')} | {subj} | {r.get('delivered')} | {r.get('unique_opens')} | "
            f"{r.get('unique_clicks')} | {r.get('open_rate_pct')} | {r.get('ctor_pct')} | {health} |"
        )
    if not rows:
        lines.append("| — | 데이터 없음 | — | — | — | — | — | — |")
    lines.extend(
        [
            "",
            "## 기록 방법",
            "```bash",
            "scripts/newsletter-ctor-record.sh YYYY-MM-DD --delivered N --opens N --clicks N",
            "scripts/newsletter-ctor-dashboard.sh",
            "```",
        ]
    )
    return "\n".join(lines)


def build_dashboard_html(records: list[dict[str, Any]] | None = None) -> str:
    rows = records if records is not None else list_records()
    lo, hi, o_lo, o_hi = _ctor_targets()
    tpl = read_template("templates/dashboard/newsletter-ctor.html")
    tr_html = ""
    for r in rows:
        badge = "ok" if r.get("ctor_health") == "healthy" else "warn"
        tr_html += (
            f"<tr><td>{r.get('stamp')}</td>"
            f"<td>{truncate(r.get('subject') or '—', 48)}</td>"
            f"<td class='num'>{r.get('delivered')}</td>"
            f"<td class='num'>{r.get('unique_opens')}</td>"
            f"<td class='num'>{r.get('unique_clicks')}</td>"
            f"<td class='num'>{r.get('open_rate_pct')}%</td>"
            f"<td class='num'><span class='badge {badge}'>{r.get('ctor_pct')}%</span></td></tr>\n"
        )
    if not tr_html:
        tr_html = "<tr><td colspan='7'>실측 데이터 없음 — newsletter-ctor-record.sh 로 기록</td></tr>"
    latest = rows[0] if rows else {}
    summary = (
        f"최근 호 CTOR {latest.get('ctor_pct', '—')}% · Open {latest.get('open_rate_pct', '—')}%"
        if latest
        else "실측 캠페인 없음"
    )
    return (
        tpl.replace("{{CTOR_TARGET}}", f"{lo}–{hi}%")
        .replace("{{OPEN_TARGET}}", f"{o_lo}–{o_hi}%")
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
        return {"count": 0}
    healthy = sum(1 for r in records if r.get("ctor_health") == "healthy")
    avg_ctor = round(sum(float(r.get("ctor_pct") or 0) for r in records) / len(records), 2)
    return {
        "count": len(records),
        "healthy_count": healthy,
        "avg_ctor_pct": avg_ctor,
        "latest": records[0],
    }
