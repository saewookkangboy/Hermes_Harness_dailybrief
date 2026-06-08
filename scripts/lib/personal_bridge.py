"""Brief ↔ Personal bridge — 메일·개인 메모 → brief 후보 큐."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from lib.common import studio_today, truncate

WORKDIR = Path.home() / "hermes-content-studio"
PERSONAL_DIR = WORKDIR / "content" / "personal"
INBOX_PATH = PERSONAL_DIR / "_inbox_candidates.json"

ACTION_PATTERNS = [
    re.compile(r"(?:action|액션|할일|todo|follow.?up)[:：]\s*(.+)", re.I),
    re.compile(r"(?:제안|인사이트|키워드)[:：]\s*(.+)", re.I),
    re.compile(r"^[-*]\s+(.{12,120})$", re.M),
]

TOPIC_HINTS = re.compile(
    r"\b(AX|AI|에이전트|AEO|마케팅|리서치|브리프|콘텐츠|Notion|Kurly|Claude|Gemini)\b",
    re.I,
)


def load_inbox() -> dict:
    if not INBOX_PATH.exists():
        return {"version": 1, "candidates": [], "updated_at": ""}
    try:
        return json.loads(INBOX_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "candidates": [], "updated_at": ""}


def save_inbox(data: dict) -> None:
    PERSONAL_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    INBOX_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_lines(text: str) -> list[str]:
    found: list[str] = []
    for pat in ACTION_PATTERNS:
        for m in pat.finditer(text):
            line = m.group(1).strip()
            if len(line) >= 8 and line not in found:
                found.append(line)
    for m in TOPIC_HINTS.finditer(text):
        kw = m.group(0)
        if kw not in found:
            found.append(f"키워드: {kw}")
    return found[:10]


def scan_personal_files(stamp: str | None = None) -> list[dict]:
    """content/personal/* 에서 brief 후보 추출."""
    stamp = stamp or studio_today()
    candidates: list[dict] = []
    if not PERSONAL_DIR.is_dir():
        return candidates
    for path in sorted(PERSONAL_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(_extract_lines(text), 1):
            candidates.append(
                {
                    "id": f"{path.stem}:{i}",
                    "source": str(path.relative_to(WORKDIR)),
                    "stamp": stamp,
                    "text": truncate(line, 200),
                    "status": "pending",
                }
            )
    return candidates


def merge_inbox(new_items: list[dict], *, max_items: int = 20) -> dict:
    data = load_inbox()
    existing_ids = {c.get("id") for c in data.get("candidates", [])}
    for item in new_items:
        if item["id"] not in existing_ids:
            data.setdefault("candidates", []).append(item)
    data["candidates"] = data["candidates"][-max_items:]
    save_inbox(data)
    return data


def sync_inbox_from_personal(stamp: str | None = None) -> dict:
    items = scan_personal_files(stamp)
    return merge_inbox(items)


def format_inbox_summary() -> str:
    data = load_inbox()
    items = [c for c in data.get("candidates", []) if c.get("status") == "pending"]
    if not items:
        return "📥 Brief 후보 큐: 비어 있음"
    lines = [f"📥 Brief 후보 큐 ({len(items)}건)", ""]
    for c in items[:7]:
        lines.append(f"• [{c.get('source', '?')}] {c.get('text', '')}")
    return "\n".join(lines)


def queue_topic_for_brief(topic: str, *, source: str = "deep-intent") -> dict:
    item = {
        "id": f"{source}:{hash(topic) & 0xFFFFFF:06x}",
        "source": source,
        "stamp": studio_today(),
        "text": truncate(topic, 200),
        "status": "pending",
    }
    return merge_inbox([item])
