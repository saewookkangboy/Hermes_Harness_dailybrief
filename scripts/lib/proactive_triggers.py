"""Proactive Commander — 조건 트리거 알림 (Phase 1 + P1–P8 확장)."""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from lib.brief_gate import brief_path, needs_daily_research
from lib.common import studio_today

WORKDIR = Path.home() / "hermes-content-studio"
STATE_PATH = WORKDIR / "content" / ".notion-archive-state.json"
METRICS_PATH = WORKDIR / ".harness" / "newsletter-ctor-metrics.json"
MAX_NOTION_STALE_HOURS = 24
MAX_CTOR_STALE_DAYS = 7
SEND_DAYS = {"tue", "wed"}


def _notion_last_sync_ts(stamp: str) -> float | None:
    if not STATE_PATH.exists():
        return None
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    day = (state.get("days") or {}).get(stamp)
    if not isinstance(day, dict):
        return None
    pages = state.get("pages") or {}
    prefix = f"{stamp}/"
    latest = 0.0
    for key, meta in pages.items():
        if not key.startswith(prefix) or not isinstance(meta, dict):
            continue
        ts = meta.get("synced_at") or meta.get("updated_at")
        if isinstance(ts, (int, float)):
            latest = max(latest, float(ts))
    if latest:
        return latest
    mtime = STATE_PATH.stat().st_mtime
    return mtime if pages else None


def check_brief_freshness(stamp: str) -> str | None:
    if not brief_path(stamp).exists():
        return f"⚠️ {stamp} Brief 없음 — run-research-brief.sh 실행 권장"
    if needs_daily_research(stamp):
        return f"⚠️ {stamp} Brief 신선도 미달 — M1 재수집 권장"
    return None


def check_notion_stale(stamp: str, *, max_hours: int = MAX_NOTION_STALE_HOURS) -> str | None:
    ts = _notion_last_sync_ts(stamp)
    if ts is None:
        return f"⚠️ {stamp} Notion 동기화 기록 없음 — archive-to-notion.sh --force 권장"
    age_h = (time.time() - ts) / 3600
    if age_h > max_hours:
        return f"⚠️ Notion sync {age_h:.0f}h 경과 — 재동기화 권장"
    return None


def check_newsletter_paste_missing(stamp: str) -> str | None:
    """발송일(화·수) 전 paste pack 미생성 알림."""
    today = datetime.now(timezone.utc).astimezone()
    weekday = today.strftime("%a").lower()[:3]
    if weekday not in SEND_DAYS:
        return None
    paste = WORKDIR / "content" / "packages" / f"{stamp}_newsletter-paste.md"
    if paste.exists():
        return None
    return f"⚠️ {stamp} 뉴스레터 paste 팩 없음 — run-newsletter.sh --validate 권장 (발송일 {weekday})"


def check_ctor_stale(*, max_days: int = MAX_CTOR_STALE_DAYS) -> str | None:
    if not METRICS_PATH.exists():
        return f"⚠️ CTOR 실측 {max_days}일 미기록 — newsletter-ctor-record.sh 권장"
    try:
        data = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        records = data.get("records") or []
        if not records:
            return f"⚠️ CTOR 실측 없음 — newsletter-ctor-record.sh 권장"
        latest = records[0].get("recorded_at", "")
        if not latest:
            return None
        ts = datetime.strptime(latest, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age_d = (datetime.now(timezone.utc) - ts).days
        if age_d > max_days:
            return f"⚠️ CTOR 실측 {age_d}일 경과 — newsletter-ctor-record.sh 갱신 권장"
    except (json.JSONDecodeError, OSError, ValueError):
        return "⚠️ CTOR 메트릭 파싱 실패 — .harness/newsletter-ctor-metrics.json 확인"
    return None


def check_watch_telegram_duplicates() -> str | None:
    script = WORKDIR / "scripts" / "kill-stale-watch-telegram.sh"
    if not script.exists():
        return None
    try:
        out = subprocess.run(
            ["bash", str(script), "--check"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if "DUPLICATE" in (out.stdout or ""):
            return "⚠️ watch-telegram 중복 프로세스 — kill-stale-watch-telegram.sh 실행 권장"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def run_proactive_checks(stamp: str | None = None) -> list[dict[str, str]]:
    stamp = stamp or studio_today()
    checks: list[tuple[str, str | None]] = [
        ("brief_freshness", check_brief_freshness(stamp)),
        ("notion_stale", check_notion_stale(stamp)),
        ("newsletter_paste", check_newsletter_paste_missing(stamp)),
        ("ctor_stale", check_ctor_stale()),
        ("watch_telegram", check_watch_telegram_duplicates()),
    ]
    alerts: list[dict[str, str]] = []
    for check_id, msg in checks:
        if msg:
            alerts.append({"id": check_id, "stamp": stamp, "message": msg})
    return alerts


def format_proactive_block(alerts: list[dict[str, str]]) -> str:
    if not alerts:
        return "✅ Proactive: 이상 없음"
    lines = ["🔔 Proactive 알림", ""]
    for a in alerts:
        lines.append(a["message"])
    return "\n".join(lines)
