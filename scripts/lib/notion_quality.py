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
    fact_checked: bool = False
    fact_check_issues: list[str] = field(default_factory=list)


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
    "newsletter": 800,
    "newsletter_html": 1200,
    "newsletter_paste": 600,
    "lecture_outline": 500,
    "lecture_html": 800,
}

REQUIRED_MARKERS = {
    "research": ["## Executive Summary", "## Top 7"],
    "blog": ["## 한 줄 요약", "## FAQ"],
    "unified": ["## Executive Context", "## Top 인사이트", "## Research Brief 발췌", "| # |"],
    "instagram": ["## 플랫폼", "## 캐러셀", "## Gemini 이미지 생성 프롬프트"],
    "linkedin": ["## 포스트 구조", "## CTA", "## Gemini 이미지 생성 프롬프트"],
    "newsletter": ["Newsletter 컨텍스트", "CTOR", "제목 A/B"],
    "newsletter_html": ["30초 TLDR", "이번 주 실습"],
    "newsletter_paste": ["붙여넣기 팩", "§1 제목", "§3 본문"],
}

FACT_CHECK_CATEGORIES = {
    "unified",
    "research",
    "blog",
    "instagram",
    "linkedin",
    "lecture_outline",
}

SOURCE_URL_RE = re.compile(r"https?://[^\s)\]>]+", re.I)
HIGH_RISK_NUMERIC_RE = re.compile(
    r"(?:\d+(?:\.\d+)?\s?(?:%|퍼센트|조|억|만|원|달러|USD|KRW)|"
    r"(?:증가|감소|성장|하락|상승|점유율|매출|투자|사용자|MAU|DAU))",
    re.I,
)
ABSOLUTE_CLAIM_RE = re.compile(r"(세계\s*최초|국내\s*최초|유일한|반드시|확실히|항상|전혀)")


def fact_check_content(text: str, cat_key: str, cfg: dict) -> tuple[bool, list[str], int]:
    """Notion 반영 전 결정적 팩트체크 게이트.

    LLM 없이 확인 가능한 최소 기준만 평가합니다.
    - 데이터/인용형 카테고리는 출처 URL을 요구합니다.
    - 숫자·최상급·절대 표현은 출처가 없으면 draft로 낮춥니다.
    - 최종 Notion 메타에 통과/이슈가 남도록 QualityResult에 반영합니다.
    """
    fcfg = (_quality_cfg(cfg).get("fact_check") or {}) if cfg else {}
    enabled = bool(fcfg.get("enabled", True))
    categories = set(fcfg.get("categories") or FACT_CHECK_CATEGORIES)
    if not enabled or cat_key not in categories:
        return False, [], 0

    issues: list[str] = []
    urls = SOURCE_URL_RE.findall(text)
    has_url = bool(urls)
    has_high_risk_numeric = bool(HIGH_RISK_NUMERIC_RE.search(text))
    has_absolute_claim = bool(ABSOLUTE_CLAIM_RE.search(text))

    if not has_url:
        issues.append("팩트체크 실패: 출처 URL 없음")
    if (has_high_risk_numeric or has_absolute_claim) and not has_url:
        issues.append("팩트체크 실패: 수치·최상급 주장에 검증 URL 없음")

    minimum_urls = int(fcfg.get("minimum_urls", 1))
    if has_url and len(set(urls)) < minimum_urls:
        issues.append(f"팩트체크 주의: 출처 URL {len(set(urls))}개 < {minimum_urls}개")

    penalty = 0
    if issues:
        penalty = int(fcfg.get("penalty", 30))
    return True, issues, penalty


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

    fact_checked, fact_issues, fact_penalty = fact_check_content(text, cat_key, cfg)
    if fact_issues:
        issues.extend(fact_issues)
        score -= fact_penalty

    score = max(0, min(100, score))
    ok = score >= min_score and not fact_issues
    tier = "canonical" if ok else "draft"
    return QualityResult(
        ok=ok,
        score=score,
        tier=tier,
        issues=issues,
        fact_checked=fact_checked,
        fact_check_issues=fact_issues,
    )
