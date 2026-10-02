"""뉴스레터 발행 이력 원장 — 신선도·패턴 로테이션용 (결정적)."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

WORKDIR = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER = WORKDIR / "content" / "newsletter" / "issue-ledger.jsonl"
_TOPIC_RE = re.compile(r"[^0-9a-zA-Z가-힣]+")


def ledger_path(cfg: dict | None = None) -> Path:
    fresh = (cfg or {}).get("freshness") or {}
    rel = fresh.get("ledger_path") or "content/newsletter/issue-ledger.jsonl"
    path = Path(rel)
    return path if path.is_absolute() else WORKDIR / path


def topic_key(text: str) -> str:
    """정규화된 주제 키 — 비교용."""
    t = _TOPIC_RE.sub(" ", (text or "").lower())
    parts = [p for p in t.split() if len(p) >= 2][:8]
    return "-".join(parts) if parts else "unknown"


def hero_hash(text: str) -> str:
    norm = " ".join((text or "").split()).lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def read_ledger(cfg: dict | None = None, *, limit: int = 50) -> list[dict[str, Any]]:
    path = ledger_path(cfg)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    rows.sort(key=lambda r: str(r.get("stamp") or ""), reverse=True)
    return rows[:limit]


def recent_excluding(
    stamp: str,
    cfg: dict | None = None,
    *,
    lookback: int | None = None,
) -> list[dict[str, Any]]:
    fresh = (cfg or {}).get("freshness") or {}
    n = lookback if lookback is not None else int(fresh.get("lookback_issues", 7))
    return [r for r in read_ledger(cfg, limit=n + 5) if r.get("stamp") != stamp][:n]


def append_issue(
    stamp: str,
    *,
    topic: str,
    subject: str,
    pattern_id: str,
    urls: list[str],
    hero: str,
    reasons: list[str] | None = None,
    cfg: dict | None = None,
) -> Path:
    path = ledger_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    # rewrite same stamp if regenerating
    existing = [r for r in read_ledger(cfg, limit=200) if r.get("stamp") != stamp]
    row = {
        "stamp": stamp,
        "topic_key": topic_key(topic),
        "topic": topic,
        "subject": subject,
        "pattern_id": pattern_id,
        "urls": [u for u in urls if u],
        "hero_hash": hero_hash(hero),
        "reasons": reasons or [],
    }
    existing.insert(0, row)
    existing.sort(key=lambda r: str(r.get("stamp") or ""), reverse=True)
    with path.open("w", encoding="utf-8") as f:
        for item in existing[:90]:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return path
