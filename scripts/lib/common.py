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


@lru_cache(maxsize=8)
def read_template(rel_path: str) -> str:
    """Cache template reads (blog HTML, etc.)."""
    path = WORKDIR / rel_path
    return path.read_text(encoding="utf-8")
