"""Deterministic Velog daily-report builders for AI Agent trends."""
from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import date

from lib.common import compress_sentences, finish_at_sentence, read_template, slugify
from lib.content_quality import Insight
from lib.humanize_korean import humanize

BODY_MAX_CHARS = 3000
H2_TRENDS = "## 1. 주요 트렌드 및 개발 이슈"
H2_TECH = "## 2. 요즘 주목받는 핵심 기술"
H2_IMPLICATIONS = "## 3. 마케터 및 비즈니스 리더를 위한 향후 대책"


@dataclass
class DailyBlogReport:
    stamp: str
    slug: str
    title: str
    meta_description: str
    prologue: list[str]
    trend_blocks: list[tuple[str, list[str]]]
    tech_bullets: list[str]
    implications: list[str]
    sources: list[tuple[str, str]]
    one_liner: str


def body_char_count(md: str) -> int:
    """Return len of MD excluding sources and its SEO tail."""
    cut_points = [
        index
        for marker in ("\n## 출처", "\n🔗 출처", "\n## SEO")
        if (index := md.find(marker)) >= 0
    ]
    text = md[: min(cut_points)] if cut_points else md
    return len(text)


def _theme_title(insights: list[Insight]) -> str:
    return insights[0].korean_title if insights else "AI 에이전트 동향"


def _stamp_parts(stamp: str) -> tuple[str, int, int, str]:
    try:
        parsed = date.fromisoformat(stamp)
    except ValueError:
        return stamp[:4] or "2026", 1, 1, stamp[-5:].replace("-", "/")
    return str(parsed.year), parsed.month, parsed.day, parsed.strftime("%m/%d")


def _sentence(text: str, max_chars: int) -> str:
    return compress_sentences((text or "").strip(), max_chars, max_sentences=2)


def _first_nonempty(*values: str) -> str:
    return next((value.strip() for value in values if value and value.strip()), "")


def _build_report(stamp: str, summary: str, insights: list[Insight]) -> DailyBlogReport:
    year, month, day, short_date = _stamp_parts(stamp)
    theme = _theme_title(insights)
    title = f"[오늘의 AI 트렌드] {theme}({short_date})"
    lead_summary = _sentence(humanize(summary or theme, genre="blog").text, 260)
    context = (
        insights[0].context_blurb(max_chars=220, max_sentences=2)
        if insights
        else "AI 에이전트의 도입은 기술 선택보다 업무 범위와 검토 기준을 먼저 정하는 데서 시작합니다."
    )
    prologue = [
        f"{year}년 {month}월 {day}일, {lead_summary}",
        _sentence(context, 220),
    ]

    trend_blocks: list[tuple[str, list[str]]] = []
    for index, insight in enumerate(insights[:2], 1):
        paragraphs = [
            _sentence(insight.korean_summary, 260),
            _sentence(insight.marketer_view, 200),
        ]
        trend_blocks.append((
            f"### {'①' if index == 1 else '②'} {insight.korean_title}",
            [item for item in paragraphs if item],
        ))

    tech_candidates = insights[2:5] or insights[:2]
    tech_bullets = [
        _sentence(
            f"{insight.korean_title}: "
            f"{_first_nonempty(insight.marketer_view, insight.utilization, insight.korean_summary)}",
            180,
        )
        for insight in tech_candidates
    ]

    implication_candidates = [
        _first_nonempty(
            insight.marketer_view,
            insight.utilization,
            insight.guides_tips,
            insight.korean_summary,
        )
        for insight in insights[:3]
    ]
    implications = [_sentence(item, 190) for item in implication_candidates if item]
    fallback_implications = [
        "에이전트가 처리할 반복 업무와 사람이 검토할 승인 지점을 함께 정하세요.",
        "작은 파일럿에서 비용, 품질, 실패 조건을 수치로 기록하세요.",
        "검증된 운영 원칙을 콘텐츠와 교육 자료로 재사용하세요.",
    ]
    implications.extend(item for item in fallback_implications if item not in implications)

    sources = [(insight.korean_title, insight.url) for insight in insights if insight.url]
    top_view = implications[0] if implications else "권한과 예산의 경계를 먼저 설계하세요."
    one_liner = _sentence(f"{theme}의 핵심은 {top_view}", 180)
    return DailyBlogReport(
        stamp=stamp,
        slug=slugify(theme),
        title=title,
        meta_description=_sentence(f"{theme} — {lead_summary}", 155),
        prologue=prologue,
        trend_blocks=trend_blocks,
        tech_bullets=tech_bullets,
        implications=implications[:3],
        sources=sources,
        one_liner=one_liner,
    )


def _render_md(report: DailyBlogReport) -> str:
    lines = [f"# {report.title}", "", *report.prologue, "", H2_TRENDS, ""]
    for heading, paragraphs in report.trend_blocks:
        lines.extend([heading, "", *paragraphs, ""])
    lines.extend([H2_TECH, ""])
    lines.extend(f"- {item}" for item in report.tech_bullets)
    lines.extend(["", H2_IMPLICATIONS, ""])
    lines.extend(f"{index}. {item}" for index, item in enumerate(report.implications, 1))
    lines.extend(["", "🔗 출처 :"])
    lines.extend(f"- {title} — {url}" for title, url in report.sources)
    lines.extend(["", f"💡 한 줄 요약: {report.one_liner}"])
    return "\n".join(lines).rstrip() + "\n"


def _shorten_md_body(md: str) -> str:
    """Shorten the longest prose paragraph while preserving headings and sources."""
    source_index = next(
        (index for marker in ("\n## 출처", "\n🔗 출처", "\n## SEO") if (index := md.find(marker)) >= 0),
        len(md),
    )
    body, tail = md[:source_index], md[source_index:]
    paragraphs = body.split("\n\n")
    candidates = [
        (len(paragraph), index)
        for index, paragraph in enumerate(paragraphs)
        if paragraph and not paragraph.startswith(("#", "-", "1.", "2.", "3.", "💡"))
    ]
    if not candidates:
        return md
    longest, index = max(candidates)
    reduced = finish_at_sentence(paragraphs[index], max(24, longest - max(80, longest // 3)))
    if reduced == paragraphs[index]:
        return md
    paragraphs[index] = reduced
    return "\n\n".join(paragraphs) + tail


def _fit_body_limit(md: str) -> str:
    while body_char_count(md) > BODY_MAX_CHARS:
        shortened = _shorten_md_body(md)
        if shortened == md:
            break
        md = shortened
    if body_char_count(md) <= BODY_MAX_CHARS:
        return md
    source_index = md.find("\n🔗 출처")
    body = finish_at_sentence(md[:source_index], BODY_MAX_CHARS)
    return f"{body}{md[source_index:]}" if source_index >= 0 else body


def build_daily_blog_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Build a Velog-style daily report with a maximum 3,000-character body."""
    return _fit_body_limit(_render_md(_build_report(stamp, summary, insights)))


def _render_sections(report: DailyBlogReport) -> str:
    chunks = ["<section>"]
    chunks.extend(f"<p>{html.escape(paragraph)}</p>" for paragraph in report.prologue)
    chunks.append("</section>")
    chunks.append(f"<section><h2>{html.escape(H2_TRENDS.removeprefix('## '))}</h2>")
    for heading, paragraphs in report.trend_blocks:
        chunks.append(f"<h3>{html.escape(heading.removeprefix('### '))}</h3>")
        chunks.extend(f"<p>{html.escape(paragraph)}</p>" for paragraph in paragraphs)
    chunks.append("</section>")
    chunks.extend(
        [
            f"<section><h2>{html.escape(H2_TECH.removeprefix('## '))}</h2><ul>",
            *(f"<li>{html.escape(item)}</li>" for item in report.tech_bullets),
            "</ul></section>",
            f"<section><h2>{html.escape(H2_IMPLICATIONS.removeprefix('## '))}</h2><ol>",
            *(f"<li>{html.escape(item)}</li>" for item in report.implications),
            "</ol></section>",
        ]
    )
    return "\n".join(chunks)


def build_daily_blog_html(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Build the HTML twin with Article JSON-LD and shared blog template."""
    report = _build_report(stamp, summary, insights)
    article_jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": report.title,
        "description": report.meta_description,
        "datePublished": stamp,
        "dateModified": stamp,
        "mainEntityOfPage": f"https://hermes-content-studio.com/blog/{report.slug}",
    }
    replacements = {
        "{{TITLE}}": html.escape(report.title),
        "{{META_DESCRIPTION}}": html.escape(report.meta_description),
        "{{CANONICAL_URL}}": f"https://hermes-content-studio.com/blog/{report.slug}",
        "{{DATE_ISO}}": stamp,
        "{{DATE_DISPLAY}}": stamp,
        "{{SUBTITLE}}": f"{stamp} AI Agent 일일 트렌드",
        "{{READ_TIME}}": "4",
        "{{DIRECT_ANSWER}}": html.escape(report.one_liner),
        "{{GEO_QUOTE}}": html.escape(report.one_liner),
        "{{SECTIONS}}": _render_sections(report),
        "{{FAQ_ITEMS}}": "",
        "{{FAQ_JSONLD}}": json.dumps(
            {"@context": "https://schema.org", "@type": "Article", "headline": report.title},
            ensure_ascii=False,
        ),
        "{{ARTICLE_JSONLD}}": json.dumps(article_jsonld, ensure_ascii=False),
        "{{SOURCES_LIST}}": "".join(
            f'<li><a href="{html.escape(url, quote=True)}">{html.escape(title)}</a></li>'
            for title, url in report.sources
        ),
        "{{TAGS}}": "AI Agent, Agentic AI, Governance, Marketing",
    }
    rendered = read_template("templates/html/blog-post.html")
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def build_threads_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Build package-companion Threads shortform with hook, points, and CTA."""
    theme = _theme_title(insights)
    hook = _sentence(humanize(summary or theme, genre="blog").text, 200)

    points: list[str] = []
    for insight in insights[:5]:
        point = _first_nonempty(
            insight.marketer_view,
            insight.korean_summary,
            insight.utilization,
        )
        if point:
            points.append(_sentence(point, 120))

    fallback_points = [
        "에이전트 권한과 승인 지점을 먼저 정하세요.",
        "최악의 손실액을 숫자로 고정하세요.",
        "작은 파일럿에서 실패 조건을 기록하세요.",
    ]
    for fallback in fallback_points:
        if len(points) >= 3:
            break
        if fallback not in points:
            points.append(fallback)
    points = points[:5]

    cta_topics: list[str] = []
    for insight in insights[:3]:
        title = insight.korean_title
        if title and title not in cta_topics:
            cta_topics.append(title)
    if not cta_topics:
        cta_topics = ["통제권", "예산", "워크플로"]
    cta_joined = "·".join(cta_topics[:3])

    lines = [
        f"# Threads — {theme} ({stamp})",
        "",
        hook,
        "",
        "핵심만 말하면:",
        *(f"→ {point}" for point in points),
        "",
        "자세한 맥락은 블로그에 정리해 두었어요.",
        "[블로그 링크]",
        "",
        f"오늘 팀에서 가장 먼저 손대고 싶은 건 {cta_joined} 중 어디인가요?",
        "댓글로 한 가지만 남겨 주세요.",
    ]
    return "\n".join(lines).rstrip() + "\n"
