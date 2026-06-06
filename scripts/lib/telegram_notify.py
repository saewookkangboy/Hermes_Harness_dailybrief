"""Telegram Bot API notifications for Content Studio pipeline."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


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
    return os.environ.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN", "")


def send_message(
    chat_id: str,
    text: str,
    *,
    disable_preview: bool = True,
) -> bool:
    token = get_bot_token()
    if not token or not chat_id:
        return False

    # Plain text — safest for Korean + URLs (no MarkdownV2 escaping issues)
    if len(text) > 4000:
        text = text[:3990] + "\n…"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_preview,
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return bool(body.get("ok"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


from lib.notify_format import (  # noqa: E402
    TOTAL_STEPS,
    format_completion,
    format_notion_pages_block,
    format_progress,
)


def format_notion_summary(day: str, pages: list[dict], *, day_url: str = "") -> str:
    return format_completion(day, pages, day_url=day_url)


def extract_chat_id_from_log(line: str) -> str:
    m = re.search(r"chat=(\d+)", line)
    return m.group(1) if m else ""
