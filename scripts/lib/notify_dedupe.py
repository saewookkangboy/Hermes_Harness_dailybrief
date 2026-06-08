"""Telegram/Slack 알림 중복 억제 — 동일 stamp·본문 해시."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
DEDUPE_PATH = WORKDIR / ".harness" / "notify-dedupe.json"
TTL_SEC = 120


def _load() -> dict:
    if not DEDUPE_PATH.exists():
        return {}
    try:
        return json.loads(DEDUPE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    DEDUPE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEDUPE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def should_skip_notify(chat_id: str, text: str, *, stamp: str = "") -> bool:
    """True면 동일 알림을 최근 TTL 내 이미 보냄."""
    if not chat_id or not text:
        return False
    key = f"{chat_id}:{stamp or 'na'}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    now = time.time()
    data = _load()
    prev = data.get(key) or {}
    if prev.get("digest") == digest and (now - float(prev.get("ts", 0))) < TTL_SEC:
        return True
    data[key] = {"digest": digest, "ts": now, "stamp": stamp}
    _save(data)
    return False
