"""Shared utilities for Hermes Content Studio scripts."""
from __future__ import annotations

import os
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

WORKDIR = Path.home() / "hermes-content-studio"


def studio_today() -> str:
    """Pipeline SoT date (default Asia/Seoul)."""
    tz = ZoneInfo(os.environ.get("STUDIO_TZ", "Asia/Seoul"))
    return datetime.now(tz).date().isoformat()


def slugify(s: str, *, max_len: int = 50) -> str:
    """Create URL-safe slug from title (Korean titles use keyword fallback)."""
    keywords: list[str] = []
    sl = s.lower()
    for kw in (
        "aeo",
        "ax-transformation",
        "ax",
        "agent",
        "seo",
        "cursor",
        "marketing",
        "automation",
    ):
        if kw.replace("-", " ") in sl or kw in sl:
            keywords.append(kw)
    s = re.sub(r"[가-힣]+", "", s)
    s = re.sub(r"[^\w\s-]", "", s.lower())
    slug = re.sub(r"[-\s]+", "-", s).strip("-")[:max_len]
    if slug and len(slug) > 2:
        return slug
    return "-".join(keywords[:2]) if keywords else "weekly"


def truncate(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= n:
        return s
    cut = s[: n - 1].rsplit(" ", 1)[0]
    return cut + "…" if cut else s[: n - 1] + "…"


def finish_at_sentence(text: str, max_chars: int) -> str:
    """max_chars 이내에서 마지막 완결 문장 경계까지 자른다 (중간 '…' 생략 없음)."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    last_end = 0
    for m in re.finditer(r"[.!?。…]", chunk):
        last_end = m.end()
    if last_end >= max(24, int(max_chars * 0.35)):
        return chunk[:last_end].strip()
    cut = chunk.rsplit(" ", 1)[0].strip()
    if cut and cut[-1] in ".!?。…":
        return cut
    return (cut or chunk.strip()) + "."


def compress_sentences(text: str, max_chars: int, *, max_sentences: int = 2) -> str:
    """완결 문장만 이어 붙여 길이 제한 (맥락 단절 방지)."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    if len(text) <= max_chars:
        return text if text[-1] in ".!?。…" else finish_at_sentence(text, max_chars)

    parts = [p.strip() for p in re.split(r"(?<=[.!?。…])\s+", text) if p.strip()]
    if not parts:
        return finish_at_sentence(text, max_chars)
    if len(parts) == 1:
        return finish_at_sentence(parts[0], max_chars)

    picked: list[str] = []
    total = 0
    for part in parts:
        if len(picked) >= max_sentences:
            break
        sep = 1 if picked else 0
        if total + sep + len(part) <= max_chars:
            picked.append(part)
            total += sep + len(part)
        elif not picked:
            return finish_at_sentence(part, max_chars)
        else:
            break
    if picked:
        out = " ".join(picked)
        if out[-1] in ".!?。…":
            return out
        return finish_at_sentence(out, max_chars)
    return finish_at_sentence(text, max_chars)


@lru_cache(maxsize=8)
def read_template(rel_path: str) -> str:
    """Cache template reads (blog HTML, etc.)."""
    path = WORKDIR / rel_path
    return path.read_text(encoding="utf-8")
