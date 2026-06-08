"""Proactive Commander — 조건 트리거 알림 (Phase 1)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from lib.brief_gate import brief_path, needs_daily_research
from lib.common import studio_today

WORKDIR = Path.home() / "hermes-content-studio"
STATE_PATH = WORKDIR / "content" / ".notion-archive-state.json"
MAX_NOTION_STALE_HOURS = 24


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


def run_proactive_checks(stamp: str | None = None) -> list[dict[str, str]]:
    stamp = stamp or studio_today()
    alerts: list[dict[str, str]] = []
    for check_id, msg in (
        ("brief_freshness", check_brief_freshness(stamp)),
        ("notion_stale", check_notion_stale(stamp)),
    ):
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
