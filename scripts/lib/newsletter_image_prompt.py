"""16:9 뉴스레터 타이틀 이미지 프롬프트 (결정적 · API 호출 없음)."""
from __future__ import annotations

from pathlib import Path

from lib.newsletter_select import SelectedIssue, display_title_for

WORKDIR = Path(__file__).resolve().parents[2]


def build_title_image_prompt(stamp: str, selected: SelectedIssue, cfg: dict | None = None) -> str:
    topic = selected.topic
    modules = [display_title_for(i, cfg) for i in selected.insights[:3]]
    metaphor = "clean editorial desk with abstract AI signal nodes and a single focal chart"
    if "AEO" in topic or "검색" in topic:
        metaphor = "search results dissolving into citation cards, soft blue data light"
    elif "광고" in topic or "Ads" in topic or "ChatGPT" in topic:
        metaphor = "chat interface with a subtle ad slot highlighted, restrained editorial lighting"
    elif "Claude" in topic or "거버넌스" in topic:
        metaphor = "secure document vault and policy checklist beside a calm AI glyph"
    elif "에이전트" in topic or "Agent" in topic or "HSAD" in topic:
        metaphor = "marketer assembling modular agent blocks on a luminous workbench"

    lines = [
        f"# Newsletter Title Image Prompt — {stamp}",
        "",
        f"**Topic:** {topic}",
        "**Aspect:** 16:9",
        "**Usage:** 이메일 히어로 · LinkedIn 뉴스레터 커버 (동일 프롬프트)",
        "",
        "## Prompt (English)",
        "",
        "```",
        f"16:9 editorial title image for a B2B AI newsletter about '{topic}'. "
        f"Visual metaphor: {metaphor}. "
        "Composition: wide cinematic frame, subject in left-center third, generous negative space on the right for optional short Korean title overlay. "
        "Style: modern Korean B2B editorial, sharp photography mixed with subtle 3D/abstract data forms, high contrast but not neon. "
        "Color: charcoal (#111), paper white, single accent crimson (#E60012), muted steel blue. "
        "Lighting: soft daylight studio, crisp edges, no lens flare. "
        "Mood: practical, authoritative, calm urgency. "
        "Include a thin red accent line as brand cue. "
        "No logos of third parties, no readable fake UI text, no watermarks, no collage clutter, no purple glow, no stock-handshake clichés.",
        "```",
        "",
        "## Overlay text (optional)",
        "",
        f"- Primary: `{topic}`",
        f"- Secondary: `{stamp} · Hermes Studio`",
        "- Placement: right third, large sans, high contrast",
        "",
        "## Alt text (접근성)",
        "",
        f"{topic}을 주제로 한 주간 B2B AI 뉴스레터 타이틀 이미지. {', '.join(modules)} 신호를 시각적으로 요약.",
        "",
        "## Forbidden",
        "",
        "- NSFW, violence, celebrity likeness",
        "- Unreadable dense paragraphs as image text",
        "- Multiple competing CTAs or QR codes",
        "",
        "## Insert slot",
        "",
        "- Email HTML: `<!-- TITLE_IMAGE_16x9 -->` 위치",
        "- LinkedIn: 원고 최상단 커버 이미지",
    ]
    return "\n".join(lines)


def write_title_image_prompt(stamp: str, selected: SelectedIssue, cfg: dict | None = None) -> Path:
    out = WORKDIR / "content" / "newsletter" / f"{stamp}_title-image-16x9.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_title_image_prompt(stamp, selected, cfg), encoding="utf-8")
    return out
