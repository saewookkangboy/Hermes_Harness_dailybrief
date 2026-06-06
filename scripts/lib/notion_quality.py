"""Notion 아카이브용 콘텐츠 품질·완성도 평가."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class QualityResult:
    ok: bool
    score: int
    tier: str  # canonical | draft
    issues: list[str] = field(default_factory=list)


DEFAULT_PLACEHOLDERS = [
    r"\bTODO\b",
    r"\bTBD\b",
    r"\bFIXME\b",
    r"lorem ipsum",
    r"\{\{[A-Z_]+\}\}",
    r"PLACEHOLDER",
    r"작성\s*중",
    r"본문\s*일부\s*생략",
    r"추후\s*작성",
    r"\.{4,}",
]

DEFAULT_MIN_CHARS = {
    "unified": 400,
    "research": 1200,
    "blog": 800,
    "instagram": 350,
    "linkedin": 350,
    "lecture_outline": 500,
    "lecture_html": 800,
}

REQUIRED_MARKERS = {
    "research": ["## Executive Summary", "## Top 7"],
    "blog": ["## 한 줄 요약", "## FAQ"],
    "unified": ["## Executive Context", "## Top 인사이트", "## Research Brief 발췌", "| # |"],
    "instagram": ["## 플랫폼", "## 캐러셀", "## Gemini 이미지 생성 프롬프트"],
    "linkedin": ["## 포스트 구조", "## CTA", "## Gemini 이미지 생성 프롬프트"],
}


def _quality_cfg(cfg: dict) -> dict:
    return (cfg.get("hygiene") or {}).get("quality") or {}


def assess_content(raw: str, cat_key: str, cfg: dict, *, path: Path | None = None) -> QualityResult:
    """콘텐츠 완성도 평가. canonical(메인) vs draft(보관) 분기."""
    qcfg = _quality_cfg(cfg)
    min_chars = (qcfg.get("min_chars") or {}).get(cat_key) or DEFAULT_MIN_CHARS.get(cat_key, 200)
    min_score = int(qcfg.get("min_score", 60))
    placeholders = qcfg.get("placeholder_patterns") or DEFAULT_PLACEHOLDERS

    text = raw.strip()
    issues: list[str] = []
    score = 100

    if len(text) < min_chars:
        issues.append(f"본문 부족 ({len(text)} < {min_chars}자)")
        score -= 35

    for pattern in placeholders:
        if re.search(pattern, text, re.I):
            issues.append(f"미완성 패턴: {pattern}")
            score -= 20
            break

    for marker in (qcfg.get("required_markers") or {}).get(cat_key) or REQUIRED_MARKERS.get(cat_key, []):
        if marker not in text:
            issues.append(f"필수 섹션 누락: {marker}")
            score -= 15

    if cat_key == "research" and not re.search(r"https?://", text):
        issues.append("출처 URL 없음")
        score -= 20

    if path and path.suffix.lower() in {".html", ".htm"}:
        if "<title>" not in text.lower():
            issues.append("HTML title 없음")
            score -= 15

    score = max(0, min(100, score))
    ok = score >= min_score
    tier = "canonical" if ok else "draft"
    return QualityResult(ok=ok, score=score, tier=tier, issues=issues)
