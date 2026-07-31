"""뉴스레터 Notion 붙여넣기 팩 — 외부 플랫폼 문서 편집기용 코드 블록."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lib.newsletter_cta import build_cta
from lib.newsletter_quality import (
    _preheader,
    _ranked_subjects,
    build_newsletter_md,
    load_newsletter_config,
)
from lib.content_quality import parse_brief
from lib.newsletter_select import select_issue_insights
from lib.newsletter_subject import format_subject_ab_block

WORKDIR = Path.home() / "hermes-content-studio"


def _paste_body_md(full_md: str) -> str:
    """발송 메타·품질 메모 제외, 타이틀 이미지/TLDR부터 본문만."""
    for marker in ("## 타이틀 이미지", "## 30초 TLDR"):
        if marker in full_md:
            body = full_md.split(marker, 1)[1]
            if "## 품질 메모" in body:
                body = body.split("## 품질 메모", 1)[0]
            return (marker + body).strip()
    return full_md.strip()


def _winner_from_scores(stamp: str) -> dict[str, Any]:
    import json

    path = WORKDIR / "content" / "newsletter" / f"{stamp}_newsletter_subject-scores.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("winner") or {}
    except (json.JSONDecodeError, OSError):
        return {}


def build_newsletter_paste_md(
    stamp: str,
    *,
    nl_md: str | None = None,
    html_text: str | None = None,
    brief_text: str | None = None,
    linkedin_md: str | None = None,
    image_prompt_md: str | None = None,
    selected=None,
) -> str:
    cfg = load_newsletter_config()
    if brief_text is None:
        brief_path = WORKDIR / "content" / "research" / f"{stamp}_brief.md"
        brief_text = brief_path.read_text(encoding="utf-8") if brief_path.exists() else ""
    summary, insights = parse_brief(brief_text)
    sel = selected or select_issue_insights(stamp, insights, cfg)
    topic = sel.topic
    ranked = _ranked_subjects(topic, stamp, cfg, sel)
    winner = ranked[0] if ranked else None
    winner_dict = _winner_from_scores(stamp)
    subject = (winner.text if winner else "") or str(winner_dict.get("text") or topic)
    score = (winner.score if winner else 0) or winner_dict.get("score", 0)
    pre = _preheader(summary, cfg)
    cta = build_cta(sel.hero, stamp, cfg)

    if nl_md is None:
        nl_md = build_newsletter_md(stamp, summary, insights, selected=sel)
    body_md = _paste_body_md(nl_md)

    if html_text is None:
        html_path = _resolve_html_path(stamp)
        html_text = html_path.read_text(encoding="utf-8") if html_path else ""

    if linkedin_md is None:
        li = WORKDIR / "content" / "linkedin" / f"{stamp}_newsletter-article.md"
        linkedin_md = li.read_text(encoding="utf-8") if li.exists() else ""

    if image_prompt_md is None:
        ip = WORKDIR / "content" / "newsletter" / f"{stamp}_title-image-16x9.md"
        image_prompt_md = ip.read_text(encoding="utf-8") if ip.exists() else ""

    ab_ref = "\n".join(format_subject_ab_block(ranked))

    lines = [
        f"# Newsletter 붙여넣기 팩 — {topic}",
        f"**날짜:** {stamp} · **배포:** Notion → 외부 뉴스레터 플랫폼 / LinkedIn Newsletter",
        "",
        "> ESP/API 자동 발송 없음. 아래 코드 블록을 **복사**해 스티비·센드그리드·메일침프·LinkedIn에 붙여넣으세요.",
        "",
        "## 붙여넣기 가이드",
        "",
        "| 단계 | 블록 | 붙여넣기 위치 |",
        "|------|------|---------------|",
        "| 1 | §1 제목 | 캠페인 제목(Subject) |",
        "| 2 | §2 프리헤더 | 미리보기 문구(Preheader) |",
        "| 3 | §3 본문 Markdown | 마크다운/리치 텍스트 에디터 |",
        "| 4 | §4 본문 HTML | HTML·소스 모드 (선택) |",
        "| 5 | §5 LinkedIn 장문 | LinkedIn Newsletter 글쓰기 |",
        "| 6 | §6 CTA URL | 버튼/링크 1곳 |",
        "| 7 | §7 16:9 이미지 프롬프트 | 외부 이미지 생성 도구 |",
        "",
        "---",
        "",
        "## §1 제목 (Subject)",
        "",
        f"**권장 (score {score}):**",
        "",
        "```",
        subject,
        "```",
        "",
        "---",
        "",
        "## §2 프리헤더 (Preheader)",
        "",
        "```",
        pre,
        "```",
        "",
        "---",
        "",
        "## §3 본문 — Markdown",
        "",
        "```",
        body_md,
        "```",
        "",
        "---",
        "",
        "## §4 본문 — HTML (선택)",
        "",
        "```html",
        (html_text or "").strip(),
        "```",
        "",
        "---",
        "",
        "## §5 LinkedIn 장문",
        "",
        "```",
        (linkedin_md or "(미생성)").strip(),
        "```",
        "",
        "---",
        "",
        "## §6 CTA URL",
        "",
        f"- **Label:** {cta.label}",
        f"- **URL:** `{cta.url or '(미확정 — https 필요)'}`",
        f"- **Reason:** {cta.reason}",
        "",
        "```",
        cta.url or "",
        "```",
        "",
        "---",
        "",
        "## §7 16:9 타이틀 이미지 프롬프트",
        "",
        "```",
        (image_prompt_md or "(미생성)").strip(),
        "```",
        "",
        "---",
        "",
        "## A/B 제목 후보 (참고)",
        "",
        ab_ref,
    ]
    return "\n".join(lines)


def _resolve_html_path(stamp: str) -> Path | None:
    nl_dir = WORKDIR / "content" / "newsletter"
    matches = sorted(nl_dir.glob(f"{stamp}_newsletter_*.html"), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


def write_paste_pack(
    stamp: str,
    *,
    nl_path: Path | None = None,
    html_path: Path | None = None,
    brief_text: str | None = None,
    linkedin_path: Path | None = None,
    image_prompt_path: Path | None = None,
    selected=None,
) -> Path:
    pkg_dir = WORKDIR / "content" / "packages"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    out = pkg_dir / f"{stamp}_newsletter-paste.md"

    nl_md = nl_path.read_text(encoding="utf-8") if nl_path and nl_path.exists() else None
    html_path = html_path or _resolve_html_path(stamp)
    html_text = html_path.read_text(encoding="utf-8") if html_path and html_path.exists() else None
    linkedin_md = (
        linkedin_path.read_text(encoding="utf-8")
        if linkedin_path and linkedin_path.exists()
        else None
    )
    image_prompt_md = (
        image_prompt_path.read_text(encoding="utf-8")
        if image_prompt_path and image_prompt_path.exists()
        else None
    )

    out.write_text(
        build_newsletter_paste_md(
            stamp,
            nl_md=nl_md,
            html_text=html_text,
            brief_text=brief_text,
            linkedin_md=linkedin_md,
            image_prompt_md=image_prompt_md,
            selected=selected,
        ),
        encoding="utf-8",
    )
    return out
