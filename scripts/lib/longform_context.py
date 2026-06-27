"""Blog · Newsletter 장문 — 컨텍스트 엔지니어링 · 완결 문장 SoT."""
from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from lib.common import compress_sentences, finish_at_sentence, read_template, slugify
from lib.content_quality import (
    Insight,
    build_faq_items,
    build_practical_application,
    expand_insight_body,
    polish_display_title,
)
from lib.humanize_korean import humanize

WORKDIR = Path.home() / "hermes-content-studio"
CONFIG_PATH = WORKDIR / "config" / "longform-content.yaml"


def load_longform_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def complete_text(
    text: str,
    max_chars: int,
    *,
    max_sentences: int | None = None,
    cfg: dict[str, Any] | None = None,
) -> str:
    """완결 문장만 — 중간 '…' 생략 금지."""
    c = cfg or load_longform_config()
    ms = max_sentences or int((c.get("sentence_policy") or {}).get("default_max_sentences", 4))
    out = compress_sentences((text or "").strip(), max_chars, max_sentences=ms)
    if out and out[-1] not in ".!?。…":
        out = finish_at_sentence(out, max_chars)
    return out


@dataclass
class BlogSection:
    heading: str
    paragraphs: list[str] = field(default_factory=list)
    list_items: list[str] = field(default_factory=list)
    level: int = 2


@dataclass
class BlogLongform:
    stamp: str
    slug: str
    title: str
    subtitle: str
    meta_description: str
    direct_answer: str
    geo_quote: str
    sections: list[BlogSection] = field(default_factory=list)
    faqs: list[tuple[str, str]] = field(default_factory=list)
    sources: list[tuple[str, str]] = field(default_factory=list)


def _blog_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("blog") or {}


def build_blog_longform(
    stamp: str,
    summary: str,
    insights: list[Insight],
    *,
    wiki_blurbs: list[str] | None = None,
) -> BlogLongform:
    cfg = load_longform_config()
    bc = _blog_cfg(cfg)
    primary = insights[0] if insights else None
    topic = polish_display_title(primary.korean_title if primary else "AI 마케팅 트렌드")
    slug = slugify(topic)

    title = complete_text(f"{topic} — 실무 가이드", int(bc.get("title_max_chars", 58)), max_sentences=1, cfg=cfg)
    subtitle = complete_text(
        f"{stamp} 주간 리서치 — SEO·AEO·GEO를 동시에 충족하는 B2B AI·AX 실행 가이드",
        int(bc.get("subtitle_max_chars", 90)),
        max_sentences=2,
        cfg=cfg,
    )
    meta = complete_text(summary, int(bc.get("meta_max_chars", 155)), max_sentences=2, cfg=cfg)
    direct = humanize(
        complete_text(
            summary,
            int(bc.get("direct_answer_max_chars", 360)),
            max_sentences=int(bc.get("direct_answer_sentences", 3)),
            cfg=cfg,
        ),
        genre="blog",
    ).text
    geo_src = (
        insights[0].context_blurb(max_chars=400, max_sentences=3) if insights else summary
    )
    geo_quote = humanize(
        complete_text(geo_src, int(bc.get("geo_quote_max_chars", 240)), max_sentences=2, cfg=cfg),
        genre="blog",
    ).text

    why_now = BlogSection(
        heading="왜 지금 이 주제인가?",
        paragraphs=[
            humanize(
                "2026년 B2B 마케팅 현장에서는 AI 검색(AEO)과 에이전트 자동화가 동시에 요구됩니다. "
                "검색 엔진과 Answer Engine은 FAQ 구조, Direct Answer, 출처 URL, 갱신일을 함께 평가합니다.",
                genre="blog",
            ).text,
            humanize(
                f"이번 주 리서치({stamp})는 {topic}을 중심으로 Top {min(len(insights), 7)} 인사이트를 "
                "하나의 아티클로 통합했습니다. 아래 본문은 모두 완결 문장으로 구성되어 "
                "블로그·FAQ JSON-LD·GEO 인용 블록에 그대로 사용할 수 있습니다.",
                genre="blog",
            ).text,
        ],
    )

    one_liner = BlogSection(
        heading="한 줄 요약 (AEO Direct Answer)",
        paragraphs=[direct],
    )

    insight_section = BlogSection(heading="핵심 인사이트 심층 분석", level=2)
    for i, ins in enumerate(insights[:7], 1):
        body = humanize(expand_insight_body(ins, i), genre="blog").text
        action_src = " ".join(
            p
            for p in (ins.opportunity or "", ins.korea_apply or "", ins.utilization or "", ins.marketer_view or "")
            if p.strip()
        )
        action = humanize(
            complete_text(
                f"실무 적용 관점에서는 {ins.korean_title} 주제를 FAQ 2개, Direct Answer 1문단, "
                f"LinkedIn 불릿 1개로 동일 메시지에 맞추는 것이 좋습니다. {action_src}",
                320,
                max_sentences=3,
                cfg=cfg,
            ),
            genre="blog",
        ).text
        insight_section.paragraphs.append(f"### {ins.korean_title}\n\n{body}\n\n{action}")

    cross = humanize(
        "AX·에이전트·AEO는 배포 레이어가 다를 뿐 메시지는 하나로 맞춰야 합니다. "
        "리서치를 한 번만 깊게 하고 블로그(Direct Answer) → LinkedIn(훅·불릿) → "
        "뉴스레터(TLDR·모듈) 순으로 재가공하면 제작 시간 대비 도달 범위를 극대화할 수 있습니다. "
        "한국 B2B는 PoC 성과만 강조하기보다 교육·체크리스트·실습 과제를 함께 제공할 때 전환이 유리합니다. "
        "Primary 키워드(AI marketing, Agentic AI, AEO)와 Long-tail 질문을 FAQ에 자연스럽게 녹이면 "
        "SEO와 AEO를 동시에 충족할 수 있습니다.",
        genre="blog",
    ).text
    cross_section = BlogSection(heading="교차 관점 — AX · 에이전트 · AEO", paragraphs=[cross])

    practical = build_practical_application(insights, summary)
    practical_section = BlogSection(
        heading="실무 적용 체크리스트",
        list_items=[humanize(step, genre="blog").text for step in practical[:8]],
    )

    wiki_section: BlogSection | None = None
    wiki_lines = [b.strip() for b in (wiki_blurbs or []) if b.strip()]
    if wiki_lines:
        wiki_section = BlogSection(
            heading="누적 Wiki 맥락",
            paragraphs=[humanize(b.lstrip("> "), genre="blog").text for b in wiki_lines[:3]],
        )

    faqs = build_faq_items(insights, summary)
    sources = [(ins.korean_title, ins.url) for ins in insights[:5] if ins.url]

    sections = [why_now, one_liner, insight_section, cross_section, practical_section]
    if wiki_section:
        sections.append(wiki_section)

    return BlogLongform(
        stamp=stamp,
        slug=slug,
        title=title,
        subtitle=subtitle,
        meta_description=meta,
        direct_answer=direct,
        geo_quote=geo_quote,
        sections=sections,
        faqs=faqs,
        sources=sources,
    )


def _section_to_html(section: BlogSection) -> str:
    tag = f"h{section.level}"
    parts = [f"<section><{tag}>{html.escape(section.heading)}</{tag}>"]
    for para in section.paragraphs:
        if para.startswith("### "):
            lines = para.split("\n\n", 1)
            h3 = lines[0].replace("### ", "").strip()
            body = lines[1] if len(lines) > 1 else ""
            parts.append(f"<h3>{html.escape(h3)}</h3>")
            for p in body.split("\n\n"):
                p = p.strip()
                if p:
                    parts.append(f"<p>{html.escape(p)}</p>")
        else:
            parts.append(f"<p>{html.escape(para)}</p>")
    if section.list_items:
        items = "".join(f"<li>{html.escape(item)}</li>" for item in section.list_items)
        parts.append(f"<ol>{items}</ol>")
    parts.append("</section>")
    return "\n".join(parts)


def render_blog_html(longform: BlogLongform) -> str:
    sections_html = "\n".join(_section_to_html(s) for s in longform.sections)

    faq_html = ""
    for q, a in longform.faqs:
        faq_html += f"""
      <div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
        <h3 itemprop="name">{html.escape(q)}</h3>
        <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
          <p itemprop="text">{html.escape(a)}</p>
        </div>
      </div>"""

    sources_html = ""
    for title, url in longform.sources:
        sources_html += f'<li><a href="{html.escape(url)}">{html.escape(title)}</a></li>'

    faq_jsonld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in longform.faqs
        ],
    }
    article_jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": longform.title,
        "alternativeHeadline": longform.subtitle,
        "datePublished": longform.stamp,
        "author": {"@type": "Organization", "name": "Hermes Content Studio"},
        "description": longform.meta_description,
    }

    template = read_template("templates/html/blog-post.html")
    replacements = {
        "{{TITLE}}": longform.title,
        "{{SUBTITLE}}": longform.subtitle,
        "{{META_DESCRIPTION}}": longform.meta_description,
        "{{CANONICAL_URL}}": f"https://content-studio.local/blog/{longform.stamp}_{longform.slug}",
        "{{DATE_ISO}}": longform.stamp,
        "{{DATE_DISPLAY}}": longform.stamp,
        "{{READ_TIME}}": "8",
        "{{DIRECT_ANSWER}}": longform.direct_answer,
        "{{SECTIONS}}": sections_html,
        "{{FAQ_ITEMS}}": faq_html,
        "{{SOURCES_LIST}}": sources_html or "<li>주간 리서치 브리프 참조</li>",
        "{{TAGS}}": "AI, AEO, GEO, Agentic AI, Marketing, AX",
        "{{FAQ_JSONLD}}": json.dumps(faq_jsonld, ensure_ascii=False, indent=2),
        "{{ARTICLE_JSONLD}}": json.dumps(article_jsonld, ensure_ascii=False, indent=2),
        "{{GEO_QUOTE}}": longform.geo_quote,
    }
    result = template
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result


def insight_paragraph_for_newsletter(ins: Insight, cfg: dict[str, Any] | None = None) -> str:
    """뉴스레터 모듈용 완결 문장 본문."""
    from lib.content_quality import _korean_source_context

    c = cfg or load_longform_config()
    nc = c.get("newsletter") or {}
    raw = _korean_source_context(ins) or ins.korean_summary or ins.marketer_view or ""
    return complete_text(
        raw,
        int(nc.get("module_context_max_chars", 420)),
        max_sentences=int(nc.get("module_context_sentences", 4)),
        cfg=cfg,
    )


def apply_sentence_for_newsletter(ins: Insight, cfg: dict[str, Any] | None = None) -> str:
    from lib.newsletter_quality import _pick_apply

    c = cfg or load_longform_config()
    nc = c.get("newsletter") or {}
    return complete_text(
        _pick_apply(ins),
        int(nc.get("module_apply_max_chars", 260)),
        max_sentences=int(nc.get("module_apply_sentences", 2)),
        cfg=cfg,
    )
