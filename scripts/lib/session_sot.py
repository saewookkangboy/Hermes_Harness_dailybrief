"""Agent session SoT — 대화·의도·pending action 영속."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKDIR = Path.home() / "hermes-content-studio"
SESSION_DIR = WORKDIR / ".harness" / "sessions"


def _session_path(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id) or "cli"
    return SESSION_DIR / f"{safe}.json"


def load_session(session_id: str = "cli") -> dict[str, Any]:
    path = _session_path(session_id)
    if not path.exists():
        return {
            "session_id": session_id,
            "last_stamp": "",
            "last_intent": "",
            "last_action": "",
            "pending_actions": [],
            "updated_at": "",
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"session_id": session_id, "pending_actions": []}


def save_session(session_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    data = load_session(session_id)
    data.update(patch)
    data["session_id"] = session_id
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _session_path(session_id).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data


def record_action(
    session_id: str,
    *,
    intent: str,
    action: str,
    stamp: str = "",
    pending: list[str] | None = None,
) -> dict[str, Any]:
    patch: dict[str, Any] = {
        "last_intent": intent,
        "last_action": action,
    }
    if stamp:
        patch["last_stamp"] = stamp
    if pending is not None:
        patch["pending_actions"] = pending
    return save_session(session_id, patch)


def resume_hint(session_id: str = "cli") -> str:
    s = load_session(session_id)
    lines: list[str] = []
    if s.get("last_stamp") and s.get("last_action"):
        lines.append(
            f"이전 세션: {s['last_stamp']} · {s.get('last_intent', '')} → {s['last_action']}"
        )
    pending = s.get("pending_actions") or []
    if pending:
        lines.append("대기: " + ", ".join(pending[:3]))
    return "\n".join(lines) if lines else ""
