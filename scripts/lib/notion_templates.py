"""Notion archive templates — normalize package markdown before upload."""
from __future__ import annotations

import re
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"

BLOG_SECTION_TITLES = frozenset(
    {"한 줄 요약", "실무 적용", "FAQ", "GEO 인용", "출처"}
)

# Insight blocks: title line followed by "N번째 인사이트"
INSIGHT_LINE_RE = re.compile(r"^\d+번째 (?:인사이트|로 살펴볼 주제)")


def normalize_blog_package(text: str) -> str:
    """Plain blog-article sections → ## headings for Notion + quality gates."""
    lines = text.splitlines()
    out: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in BLOG_SECTION_TITLES and not line.lstrip().startswith("#"):
            if out and out[-1].strip():
                out.append("")
            out.append(f"## {stripped}")
            continue
        if i == 0 and stripped and not stripped.startswith("#"):
            out.append(f"## {stripped}")
            continue
        if (
            stripped
            and not stripped.startswith("#")
            and i > 0
            and not lines[i - 1].strip()
            and not INSIGHT_LINE_RE.match(stripped)
            and stripped not in BLOG_SECTION_TITLES
            and len(stripped) < 120
            and not stripped.startswith(("Q.", "A.", "- ", "1.", "2.", "3.", "Title tag", "Meta ", "Keywords"))
            and stripped.endswith(("실무 가이드", "— 실무 가이드"))
        ):
            if out and out[-1].strip():
                out.append("")
            out.append(f"### {stripped}")
            continue
        out.append(line.rstrip())
    return "\n".join(out).strip()


def normalize_linkedin_package(text: str) -> str:
    """Ensure ## CTA section exists for quality markers."""
    if "## CTA" in text:
        return text
    if "**CTA:**" in text:
        return text.replace("**CTA:**", "## CTA\n\n**CTA:**", 1)
    return text + "\n\n## CTA\n\n이번 주 AI 마케팅 트렌드, 댓글로 공유해 주세요.\n"


def normalize_category_markdown(text: str, cat_key: str, path: Path | None = None) -> str:
    if cat_key == "blog":
        return normalize_blog_package(text)
    if cat_key == "linkedin":
        return normalize_linkedin_package(text)
    return text.strip()


def build_archive_page_body(
    label: str,
    stamp: str,
    path: Path,
    body: str,
    *,
    tier: str = "canonical",
    quality_score: int | None = None,
    quality_issues: list[str] | None = None,
    fact_checked: bool | None = None,
    fact_check_issues: list[str] | None = None,
) -> str:
    """Structured Notion page: callout meta + normalized body."""
    try:
        rel = path.relative_to(WORKDIR)
        source = str(rel)
    except ValueError:
        source = path.name

    meta_lines = [
        f"> **{label}** · `{stamp}`",
        f"> **상태:** {'✅ 정식 아카이브' if tier == 'canonical' else '📦 Draft Archive (품질 미달)'}",
        f"> **소스:** `{source}`",
    ]
    if quality_score is not None:
        meta_lines.append(f"> **품질 점수:** {quality_score}/100")
    if fact_checked is not None:
        if fact_checked and not fact_check_issues:
            meta_lines.append("> **팩트체크:** ✅ 통과 — 출처 URL·수치/최상급 주장 기준 확인")
        elif fact_checked:
            meta_lines.append("> **팩트체크:** ⚠️ 보류 — 검증 이슈로 Draft Archive 반영")
        else:
            meta_lines.append("> **팩트체크:** 제외 — 비데이터성 콘텐츠")
    if quality_issues:
        meta_lines.append(f"> **이슈:** {', '.join(quality_issues[:4])}")
    if fact_check_issues:
        meta_lines.append(f"> **팩트체크 이슈:** {', '.join(fact_check_issues[:4])}")

    meta = "\n".join(meta_lines)
    return f"{meta}\n\n---\n\n{body.strip()}\n"
