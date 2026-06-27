"""Wiki Router — index-first 검색 (Karpathy LLM Wiki · memory_router 연동)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lib.common import truncate

WORKDIR = Path.home() / "hermes-content-studio"
WIKI_ROOT = WORKDIR / "content" / "wiki"
INDEX_PATH = WIKI_ROOT / "index.md"
CONCEPTS_DIR = WIKI_ROOT / "concepts"
ENTITIES_DIR = WIKI_ROOT / "entities"


@dataclass
class WikiHit:
    source: str
    path: str
    snippet: str
    score: float = 0.0

    def to_memory_tuple(self) -> tuple[str, str, str, float]:
        return ("wiki", self.path, self.snippet, self.score)


def _tokenize(query: str) -> list[str]:
    q = query.lower()
    return re.findall(r"[a-z0-9가-힣]{2,}", q)[:12]


def _score_text(text: str, tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    tl = text.lower()
    return sum(1.0 for t in tokens if t in tl) / len(tokens)


def _read_snippet(path: Path, tokens: list[str], max_chars: int = 400) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not tokens:
        return truncate(text, max_chars)
    best = ""
    best_score = -1.0
    for block in re.split(r"\n{2,}", text):
        sc = _score_text(block, tokens)
        if sc > best_score:
            best_score = sc
            best = block
    if best_score <= 0:
        return truncate(text, max_chars)
    return truncate(best.strip(), max_chars)


def search_index(tokens: list[str], min_score: float = 0.25) -> list[WikiHit]:
    """Parse wiki/index.md table rows for topic_key / entity matches."""
    if not INDEX_PATH.exists() or not tokens:
        return []
    hits: list[WikiHit] = []
    text = INDEX_PATH.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if not line.startswith("|") or line.count("|") < 3:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 2 or cells[0] in ("topic_key", "엔티티", "—", "---"):
            continue
        blob = " ".join(cells)
        sc = _score_text(blob, tokens)
        if sc < min_score:
            continue
        key = cells[0]
        concept = CONCEPTS_DIR / f"{key}.md"
        entity = ENTITIES_DIR / f"{key}.md"
        rel = (
            str(concept.relative_to(WORKDIR))
            if concept.exists()
            else str(INDEX_PATH.relative_to(WORKDIR))
        )
        hits.append(
            WikiHit(
                "wiki_index",
                rel,
                f"[index] {key}: {cells[1] if len(cells) > 1 else ''}",
                sc + 0.05,
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:4]


def search_concepts(tokens: list[str], min_score: float = 0.25) -> list[WikiHit]:
    hits: list[WikiHit] = []
    if not CONCEPTS_DIR.is_dir() or not tokens:
        return hits
    for path in sorted(CONCEPTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        sc = _score_text(text, tokens)
        if sc < min_score:
            continue
        hits.append(
            WikiHit(
                "wiki_concept",
                str(path.relative_to(WORKDIR)),
                _read_snippet(path, tokens),
                sc,
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:4]


def search_entities(tokens: list[str], min_score: float = 0.25) -> list[WikiHit]:
    hits: list[WikiHit] = []
    if not ENTITIES_DIR.is_dir() or not tokens:
        return hits
    for path in sorted(ENTITIES_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        sc = _score_text(text, tokens)
        if sc < min_score:
            continue
        hits.append(
            WikiHit(
                "wiki_entity",
                str(path.relative_to(WORKDIR)),
                _read_snippet(path, tokens),
                sc,
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:2]


def route_wiki(query: str, min_score: float = 0.25) -> list[WikiHit]:
    """index-first → concepts → entities."""
    tokens = _tokenize(query)
    if not tokens:
        return []
    seen: set[str] = set()
    merged: list[WikiHit] = []
    for batch in (
        search_index(tokens, min_score),
        search_concepts(tokens, min_score),
        search_entities(tokens, min_score),
    ):
        for h in batch:
            if h.path in seen:
                continue
            seen.add(h.path)
            merged.append(h)
    merged.sort(key=lambda x: x.score, reverse=True)
    return merged[:6]
