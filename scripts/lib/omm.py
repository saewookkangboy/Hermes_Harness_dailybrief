"""OMM — Operational Memory Mistakes: 반복 실수 기록 → 다음 세션 방어선."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKDIR = Path.home() / "hermes-content-studio"
OMM_PATH = WORKDIR / ".harness" / "omm.jsonl"
JARVIS_PATH = WORKDIR / "JARVIS.md"

REQUIRED_JARVIS_SECTIONS = ("NOW", "LAW", "BAN", "MAP", "OMM", "RAW")


def record_omm(mistake: str, defense: str, *, context: str = "", source: str = "manual") -> dict[str, Any]:
    """실수·방어선 한 건 append. 반환: 기록 dict."""
    OMM_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "mistake": mistake.strip(),
        "defense": defense.strip(),
        "context": context.strip(),
        "source": source.strip() or "manual",
    }
    with OMM_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_omm(limit: int = 20) -> list[dict[str, Any]]:
    if not OMM_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in OMM_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def format_omm_block(limit: int = 5) -> str:
    rows = read_omm(limit)
    if not rows:
        return "- (OMM 기록 없음)"
    lines: list[str] = []
    for row in rows[-limit:]:
        date = row.get("date") or row.get("ts", "")[:10]
        mistake = row.get("mistake", "")
        defense = row.get("defense", "")
        lines.append(f"- **{date}** {mistake} → `{defense}`")
    return "\n".join(lines)


def validate_jarvis_md() -> tuple[bool, list[str]]:
    """JARVIS.md 필수 섹션 검증."""
    errors: list[str] = []
    if not JARVIS_PATH.exists():
        return False, ["JARVIS.md missing"]
    text = JARVIS_PATH.read_text(encoding="utf-8")
    for section in REQUIRED_JARVIS_SECTIONS:
        if f"## {section}" not in text:
            errors.append(f"missing section: {section}")
    return len(errors) == 0, errors
