"""Wiki concept lookup — M2 다운스트림 주입 (결정적)."""
from __future__ import annotations

import re
from pathlib import Path

from lib.common import compress_sentences, truncate
from lib.content_quality import Insight, _insight_topic_key

WORKDIR = Path.home() / "hermes-content-studio"
CONCEPTS_DIR = WORKDIR / "content" / "wiki" / "concepts"


def _slug_safe(key: str) -> str:
    s = re.sub(r"[^\w\-가-힣]", "_", key.strip().lower())
    return s[:64] or "general"


def concept_path_for_topic(topic_key: str) -> Path:
    return CONCEPTS_DIR / f"{_slug_safe(topic_key)}.md"


def read_concept_summary(topic_key: str, *, max_chars: int = 200) -> str:
    """wiki/concepts/{topic_key}.md 에서 ## 최신 요약 추출."""
    path = concept_path_for_topic(topic_key)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"## 최신 요약\s*\n+(.+?)(?:\n## |\Z)", text, re.S)
    if not m:
        return ""
    raw = m.group(1).strip()
    return compress_sentences(raw, max_chars, max_sentences=2) or truncate(raw, max_chars)


def wiki_blurb_for_insight(ins: Insight) -> str:
    key = _insight_topic_key(ins)
    summary = read_concept_summary(key)
    if not summary:
        return ""
    return f"> **Wiki 맥락 ({key}):** {summary}"


def inject_wiki_blurbs(insights: list[Insight]) -> list[str]:
    """인사이트별 wiki 블록 — 없으면 빈 문자열."""
    return [wiki_blurb_for_insight(ins) for ins in insights]


def wiki_injection_available() -> bool:
    return CONCEPTS_DIR.is_dir() and any(CONCEPTS_DIR.glob("*.md"))
