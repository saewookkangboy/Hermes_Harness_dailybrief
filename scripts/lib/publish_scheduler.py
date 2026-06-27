"""HITL Publish Scheduler — 예약 발행 + cron HITL 카드 전송."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from lib.publish_gate import (
    VALID_CHANNELS,
    format_telegram_approval,
    load_queue,
    request_publish,
)

WORKDIR = Path.home() / "hermes-content-studio"
SCHEDULE_DIR = WORKDIR / ".harness" / "publish-schedule"
KST = ZoneInfo("Asia/Seoul")


def _now_kst() -> datetime:
    return datetime.now(KST)


def _parse_at(when: str, ref: datetime | None = None) -> datetime:
    """Parse schedule time in KST — YYYY-MM-DD HH:MM | HH:MM | +30m | +2h."""
    ref = ref or _now_kst()
    when = when.strip()

    m = re.match(r"^\+(\d+)(m|h)$", when, re.I)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        delta = timedelta(minutes=n) if unit == "m" else timedelta(hours=n)
        return ref + delta

    m = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}):(\d{2})$", when)
    if m:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3)}", "%Y-%m-%d %H:%M").replace(tzinfo=KST)

    m = re.match(r"^(\d{1,2}):(\d{2})$", when)
    if m:
        candidate = ref.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        if candidate <= ref:
            candidate += timedelta(days=1)
        return candidate

    raise ValueError(f"스케줄 형식: YYYY-MM-DD HH:MM | HH:MM | +30m | +2h (got {when!r})")


def _schedule_path(schedule_id: str) -> Path:
    return SCHEDULE_DIR / f"{schedule_id}.json"


def schedule_publish(
    stamp: str,
    channels: list[str],
    when: str,
    *,
    note: str = "",
) -> dict[str, Any]:
    """HITL 발행 예약 — due 시 HITL 카드 전송 (자동 승인 없음)."""
    chs = [c.lower() for c in channels if c.lower() in VALID_CHANNELS]
    if not chs:
        chs = ["linkedin"]
    at = _parse_at(when)
    schedule_id = f"{stamp}_{at.strftime('%Y%m%d%H%M')}_{uuid.uuid4().hex[:6]}"
    payload = {
        "id": schedule_id,
        "stamp": stamp,
        "channels": chs,
        "scheduled_at": at.isoformat(),
        "scheduled_at_kst": at.strftime("%Y-%m-%d %H:%M KST"),
        "status": "pending",
        "note": note,
        "created_at": _now_kst().isoformat(),
    }
    SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)
    _schedule_path(schedule_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def list_schedules(*, stamp: str = "", include_done: bool = False) -> list[dict[str, Any]]:
    SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    for path in sorted(SCHEDULE_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if stamp and data.get("stamp") != stamp:
            continue
        if not include_done and data.get("status") in ("notified", "cancelled"):
            continue
        out.append(data)
    return out


def cancel_schedule(schedule_id: str) -> dict[str, Any] | None:
    path = _schedule_path(schedule_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = "cancelled"
    data["cancelled_at"] = _now_kst().isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def process_due_schedules(*, notify: bool = True) -> list[dict[str, Any]]:
    """cron: due 예약 → publish_queue + HITL 카드."""
    now = _now_kst()
    processed: list[dict[str, Any]] = []
    for data in list_schedules(include_done=True):
        if data.get("status") != "pending":
            continue
        try:
            at = datetime.fromisoformat(data["scheduled_at"])
            if at.tzinfo is None:
                at = at.replace(tzinfo=KST)
        except (KeyError, ValueError):
            continue
        if at > now:
            continue
        stamp = data["stamp"]
        channels = data.get("channels") or ["linkedin"]
        queue = request_publish(stamp, channels)
        data["status"] = "notified"
        data["notified_at"] = now.isoformat()
        data["queue_status"] = queue.get("status")
        _schedule_path(data["id"]).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        msg = format_schedule_notify(data, queue)
        if notify:
            _commander_notify(msg)
        processed.append({**data, "notify_message": msg})
    return processed


def _commander_notify(msg: str) -> None:
    import subprocess

    subprocess.run(
        ["bash", str(WORKDIR / "scripts" / "lib" / "commander_notify.sh"), "notify", msg],
        check=False,
        cwd=str(WORKDIR),
    )


def format_schedule_notify(schedule: dict[str, Any], queue: dict[str, Any] | None = None) -> str:
    stamp = schedule.get("stamp", "")
    q = queue or load_queue(stamp)
    lines = [
        f"⏰ HITL 발행 예약 도래 · {stamp}",
        f"예정: {schedule.get('scheduled_at_kst', schedule.get('scheduled_at', ''))}",
        f"채널: {', '.join(schedule.get('channels') or [])}",
        "",
        format_telegram_approval(stamp, q),
    ]
    if schedule.get("note"):
        lines.insert(3, f"메모: {schedule['note']}")
    return "\n".join(lines)


def format_schedule_list(schedules: list[dict[str, Any]]) -> str:
    if not schedules:
        return "📭 발행 예약 없음"
    lines = ["📅 HITL Publish Schedule", ""]
    for s in schedules[:10]:
        icon = {"pending": "⏳", "notified": "📬", "cancelled": "❌"}.get(s.get("status", ""), "·")
        lines.append(
            f"{icon} `{s.get('id', '')[:24]}…` · {s.get('stamp')} · "
            f"{s.get('scheduled_at_kst', '')} · {', '.join(s.get('channels') or [])}"
        )
    lines.extend(["", "취소: hermes-agent.sh schedule --cancel --id SCHEDULE_ID"])
    return "\n".join(lines)


def format_schedule_created(data: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"✅ 발행 예약 · {data.get('stamp')}",
            "",
            f"⏰ {data.get('scheduled_at_kst')}",
            f"📢 채널: {', '.join(data.get('channels') or [])}",
            f"🆔 {data.get('id')}",
            "",
            "due 시 HITL 카드가 Telegram/Slack으로 전송됩니다.",
            "승인: hermes-agent.sh approve linkedin --date {stamp}".format(stamp=data.get("stamp")),
        ]
    )
