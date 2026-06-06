"""Slack Web API notifications for Content Studio pipeline."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

SLACK_TEXT_LIMIT = 3900
SLACK_CHUNK_BODY = 3500


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def get_bot_token() -> str:
    env = load_env()
    raw = os.environ.get("SLACK_BOT_TOKEN") or env.get("SLACK_BOT_TOKEN", "")
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return ""
    # Multi-workspace: use primary (first) token
    return raw.split(",")[0].strip()


def send_message(channel_id: str, text: str, *, thread_ts: str | None = None) -> bool:
    token = get_bot_token()
    if not token or not channel_id:
        return False

    if len(text) > SLACK_TEXT_LIMIT:
        text = text[: SLACK_TEXT_LIMIT - 5] + "\n…"

    body: dict[str, str] = {"channel": channel_id, "text": text}
    if thread_ts:
        body["thread_ts"] = thread_ts

    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return bool(data.get("ok"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def _split_chunks(text: str, max_len: int = SLACK_CHUNK_BODY) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    rest = text
    while rest:
        if len(rest) <= max_len:
            chunks.append(rest)
            break
        cut = rest.rfind("\n\n", 0, max_len)
        if cut < max_len // 3:
            cut = rest.rfind("\n", 0, max_len)
        if cut < max_len // 3:
            cut = max_len
        chunks.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
    return chunks


def send_long_text(channel_id: str, text: str, *, prefix: str = "") -> bool:
    """Send long markdown/text as sequential Slack messages."""
    chunks = _split_chunks(text)
    if not chunks:
        return True
    total = len(chunks)
    ok_all = True
    for i, chunk in enumerate(chunks, start=1):
        header = f"{prefix}(part {i}/{total})\n" if total > 1 and not prefix else prefix
        body = f"{header}{chunk}"
        if not send_message(channel_id, body):
            ok_all = False
    return ok_all
