"""B2B 뉴스레터 — 오픈율·완독율(CTOR) 최적화 결정적 생성."""
from __future__ import annotations

import html
import re
from pathlib import Path

import yaml

from lib.common import compress_sentences, finish_at_sentence, slugify
from lib.content_quality import Insight, parse_brief, polish_display_title
from lib.humanize_korean import humanize
from lib.newsletter_html import build_newsletter_html
from lib.newsletter_subject import (
    format_subject_ab_block,
    rank_subjects,
    save_subject_scores,
)

WORKDIR = Path.home() / "hermes-content-studio"
CONFIG_PATH = WORKDIR / "config" / "newsletter.yaml"


def load_newsletter_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _nl_short(text: str, max_chars: int, *, max_sentences: int = 2) -> str:
    """완결 문장만 — 중간 '…' 생략 금지."""
    return compress_sentences((text or "").strip(), max_chars, max_sentences=max_sentences)


def _newsletter_title(ins: Insight) -> str:
    """뉴스레터용 완결 제목 — garbage·localize 폴백."""
    for raw in (ins.korean_title, ins.title):
        t = polish_display_title(raw or "")
        if t and "신호입니다" not in t and "OpenAI News OpenAI" not in t:
            return t
    return polish_display_title(ins.title or ins.korean_title or "AI 마케팅 주간")


def _nl_label(text: str, max_chars: int) -> str:
    """인라인 제목·라벨 — polish 후 완결 문장 압축."""
    return _nl_short(polish_display_title(text or ""), max_chars, max_sentences=1)


def _pick_apply(ins: Insight) -> str:
    for field in (ins.utilization, ins.marketer_view, ins.guides_tips, ins.insight_derivation):
        val = (field or "").strip()
        if len(val) >= 20:
            return val
    return "실무 체크리스트와 사례 검증으로 팀 내 도입 우선순위를 정해 보세요."


def _subject_candidates(topic: str, stamp: str, cfg: dict | None = None) -> list[str]:
    """Stripo: 질문형·config subject_max_chars·구체성."""
    c = cfg or load_newsletter_config()
    from lib.newsletter_subject import subject_limits

    max_c, _, _ = subject_limits(c)
    t = _nl_label(topic, 32)
    templates = c.get("subject_templates") or [
        "{topic} — 지금 손댈 곳은?",
        "AX 실무, 3분이면 돼요",
        "[{stamp}] B2B AI 주간 신호",
    ]
    out: list[str] = []
    for tpl in templates:
        cand = tpl.format(topic=t, stamp=stamp)
        if len(cand) <= max_c:
            out.append(cand)
        else:
            out.append(finish_at_sentence(cand, max_c))
    return out


def _preheader(summary: str, cfg: dict | None = None) -> str:
    c = cfg or load_newsletter_config()
    max_c = int((c.get("benchmarks") or {}).get("preheader_max_chars", 40))
    s = humanize(summary, genre="linkedin").text.replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^일일 관측\([^)]+\)\s*—\s*", "", s)
    out = finish_at_sentence(s, max_c)
    if len(out) > max_c:
        out = finish_at_sentence(_nl_short(s, max_c, max_sentences=1), max_c)
    return out


def _tldr_bullets(insights: list[Insight]) -> list[str]:
    from lib.longform_context import complete_text, load_longform_config

    cfg = load_longform_config()
    nc = cfg.get("newsletter") or {}
    bullets: list[str] = []
    for ins in insights[:3]:
        title = _nl_label(_newsletter_title(ins), 40)
        body = complete_text(
            ins.korean_summary or ins.insight_derivation or ins.marketer_view or "",
            int(nc.get("tldr_body_max_chars", 120)),
            max_sentences=int(nc.get("tldr_bullet_sentences", 2)),
            cfg=cfg,
        )
        bullets.append(f"**{title}** — {body}")
    while len(bullets) < 3:
        bullets.append("이번 주 AX·AEO·에이전트 신호를 3분 안에 정리했어요.")
    return bullets


def _hero_block(ins: Insight | None, summary: str) -> str:
    from lib.longform_context import complete_text, load_longform_config

    cfg = load_longform_config()
    nc = cfg.get("newsletter") or {}
    if not ins:
        return humanize(
            complete_text(summary, 320, max_sentences=int(nc.get("hero_sentences", 4)), cfg=cfg),
            genre="linkedin",
        ).text
    title = _newsletter_title(ins)
    core = complete_text(
        ins.insight_derivation or ins.korean_summary or ins.marketer_view or "",
        280,
        max_sentences=3,
        cfg=cfg,
    )
    body = (
        f"이번 주 가장 먼저 짚을 주제는 **{title}**입니다. "
        f"{core} "
        f"현장에서는 선언형 AI보다 FAQ·실습·사례로 구매 전 검증하는 흐름이 더 강합니다. "
        f"아래 모듈은 모두 완결 문장으로 구성되어 스킵 독자와 완독 독자 모두를 위한 "
        f"SEO·AEO·GEO 인용 가능한 형태입니다."
    )
    return humanize(body, genre="linkedin").text


def _insight_module(idx: int, ins: Insight) -> str:
    """Morning Brew: 볼드 헤드라인 + 완결 문장 본문 (longform)."""
    from lib.longform_context import apply_sentence_for_newsletter, insight_paragraph_for_newsletter

    headline = _newsletter_title(ins)
    context = humanize(insight_paragraph_for_newsletter(ins), genre="linkedin").text
    apply = humanize(apply_sentence_for_newsletter(ins), genre="linkedin").text
    src = ins.url or "—"
    return "\n".join(
        [
            f"### {idx}. **{headline}**",
            "",
            context,
            "",
            f"- **현장 적용:** {apply}",
            f"- **출처:** {src}",
        ]
    )


def _grab_bag(insights: list[Insight]) -> str:
    ins = insights[0] if insights else None
    if ins and ins.market_impact:
        line = _nl_short(ins.market_impact, 140, max_sentences=2)
        return f"📊 **한 줄 데이터** — {line}"
    return "📊 **한 줄 데이터** — B2B 뉴스레터 CTOR 10–15%가 건강 구간이에요. (ClickMinded 2026)"


def _single_cta(insights: list[Insight]) -> str:
    topic = _nl_label(insights[0].korean_title if insights else "AX", 28)
    return "\n".join(
        [
            "## 이번 주 실습 1가지 (CTA)",
            "",
            f"팀 반복 업무 3개를 적고, 그중 1개만 **{topic}** 관점으로 자동화 후보를 골라보세요.",
            "",
            "→ 댓글/회신으로 공유해 주시면 다음 호에 사례를 반영할게요.",
            "",
            "**링크는 여기 1곳만:** 블로그·Notion 통합 컨텍스트에서 전문을 확인하세요. (본문 링크 분산 금지)",
        ]
    )


def _next_teaser(insights: list[Insight]) -> str:
    nxt = _nl_label(
        _newsletter_title(insights[1]) if len(insights) > 1 else "LLM 4사 주간 펄스",
        48,
    )
    return f"**다음 호 예고:** {nxt} — 심화 FAQ와 체크리스트로 이어갑니다."


def _ranked_subjects(topic: str, stamp: str, cfg: dict | None = None):
    c = cfg or load_newsletter_config()
    return rank_subjects(_subject_candidates(topic, stamp, c), c)


def _benchmark_rows(cfg: dict) -> list[str]:
    b = cfg.get("benchmarks") or {}
    ctor = b.get("ctor_target", "10-15%")
    opn = b.get("open_rate_b2b", "18-25%")
    subj = b.get("subject_max_chars", 50)
    pre = b.get("preheader_max_chars", 40)
    return [
        f"| B2B Open (방향성) | {opn} |",
        f"| CTOR | {ctor} |",
        f"| 제목 길이 | ≤{subj}자 |",
        f"| 프리헤더 | ≤{pre}자 |",
    ]


NEWSLETTER_UNIFIED_HEADING = "## Newsletter (B2B 이메일)"


def patch_unified_context_newsletter(
    stamp: str,
    ranked: list,
    nl_path: Path,
    html_path: Path,
    ctx_path: Path,
    paste_path: Path | None = None,
) -> None:
    """M2b 이후 unified-context에 뉴스레터 요약·경로 반영."""
    unified = WORKDIR / "content" / "packages" / f"{stamp}_unified-context.md"
    if not unified.exists():
        return
    cfg = load_newsletter_config()
    ctor = (cfg.get("benchmarks") or {}).get("ctor_target", "10-15%")
    winner = ranked[0] if ranked else None
    try:
        nl_rel = nl_path.relative_to(WORKDIR)
        html_rel = html_path.relative_to(WORKDIR)
        ctx_rel = ctx_path.relative_to(WORKDIR)
        paste_rel = paste_path.relative_to(WORKDIR) if paste_path else None
    except ValueError:
        nl_rel, html_rel, ctx_rel = nl_path.name, html_path.name, ctx_path.name
        paste_rel = paste_path.name if paste_path else None

    block_lines = [
        NEWSLETTER_UNIFIED_HEADING,
        "",
        f"- **CTOR 목표:** {ctor}",
        "- **배포:** Notion 붙여넣기 팩 → 외부 플랫폼 (ESP 발송 없음)",
    ]
    if winner:
        block_lines.append(f"- **권장 제목:** {winner.text} (score {winner.score})")
    block_lines.extend(
        [
            f"- **붙여넣기 팩:** `{paste_rel or f'content/packages/{stamp}_newsletter-paste.md'}`",
            f"- **본문:** `{nl_rel}`",
            f"- **HTML:** `{html_rel}`",
            f"- **컨텍스트:** `{ctx_rel}`",
            "",
        ]
    )
    new_block = "\n".join(block_lines)
    text = unified.read_text(encoding="utf-8")
    if NEWSLETTER_UNIFIED_HEADING in text:
        text = re.sub(
            rf"{re.escape(NEWSLETTER_UNIFIED_HEADING)}.*?(?=\n## |\n---\n아래 Notion)",
            new_block,
            text,
            count=1,
            flags=re.S,
        )
    else:
        marker = "\n---\n아래 Notion"
        text = text.replace(marker, f"\n{new_block}{marker}", 1) if marker in text else text + "\n\n" + new_block
    unified.write_text(text, encoding="utf-8")


def build_newsletter_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """완독율 중심 모듈형 뉴스레터 본문."""
    cfg = load_newsletter_config()
    topic = _newsletter_title(insights[0]) if insights else "AI 마케팅 주간"
    ranked = _ranked_subjects(topic, stamp, cfg)
    pre = _preheader(summary, cfg)
    ctor = (cfg.get("benchmarks") or {}).get("ctor_target", "10-15%")
    send = cfg.get("send_window") or {}
    send_note = send.get("time_kst", "10:00-11:00 KST")
    tldr = _tldr_bullets(insights)
    hero = _hero_block(insights[0] if insights else None, summary)
    modules = [_insight_module(i, ins) for i, ins in enumerate(insights[:3], 1)]

    lines = [
        f"# 주간 AI·AX 뉴스레터 — {stamp}",
        "",
        "## 발송 메타 (오픈율)",
        "",
        f"- **발신:** Hermes Studio (개인명 발신 권장 — Stripo +4~57% opens)",
        f"- **권장 발송:** {send_note} (B2B sweet spot)",
        "",
        *format_subject_ab_block(ranked),
        "",
    ]
    lines.extend(
        [
            "",
            f"**프리헤더 (≤40자):** `{pre}` ({len(pre)}자)",
            "",
            "---",
            "",
            "## 30초 TLDR",
            "",
            "*(Morning Brew 패턴 — 스킵 독자용 3불릿)*",
            "",
        ]
    )
    for b in tldr:
        lines.append(f"- {b}")
    lines.extend(
        [
            "",
            "---",
            "",
            "## 오늘의 1가지",
            "",
            hero,
            "",
            "---",
            "",
            "## 3분 읽기 — Top 3",
            "",
            "*(모듈형 · 문단 길이 점진 축소 — 완독 가속)*",
            "",
            *modules,
            "",
            "---",
            "",
            _grab_bag(insights),
            "",
            "---",
            "",
            *_single_cta(insights).splitlines(),
            "",
            "---",
            "",
            "## 다음 호",
            "",
            _next_teaser(insights),
            "",
            "---",
            "",
            "## 품질 메모",
            "",
            f"- KPI: **CTOR {ctor}** 우선 (오픈율은 MPP 보정 후 방향성만)",
            "- 구조: TLDR → Hero → 3모듈 → 단일 CTA ([Stripo 2026](https://research.stripo.email/b2b-email-open-rate-benchmarks-2026))",
            "- 레이아웃: 모바일 단일 컬럼 · 링크 1곳 ([Morning Brew modular](https://growthmodels.co/morning-brew-marketing/))",
        ]
    )
    return "\n".join(lines)


def build_newsletter_context_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Notion/에디터용 컨텍스트 패키지."""
    cfg = load_newsletter_config()
    topic = _newsletter_title(insights[0]) if insights else "주간 트렌드"
    ranked = _ranked_subjects(topic, stamp, cfg)
    read_m = (cfg.get("benchmarks") or {}).get("read_time_minutes") or [4, 6]
    lines = [
        f"# Newsletter 컨텍스트 — {topic}",
        f"**날짜:** {stamp} · **목표:** 오픈율 + 완독율(CTOR)",
        "",
        "## 벤치마크",
        "| 지표 | 목표 |",
        "|------|------|",
        *_benchmark_rows(cfg),
        f"| 읽기 시간 | {read_m[0]}–{read_m[1]}분 |",
        "",
        "## 모듈 체크리스트",
        "- [x] TLDR 3불릿",
        "- [x] Hero 1가지",
        "- [x] Insight 모듈 ×3",
        "- [x] Grab Bag 1줄",
        "- [x] Single CTA",
        "- [x] 다음 호 예고",
        "",
        "## 제목 A/B (자동 스코어)",
        "",
        *format_subject_ab_block(ranked),
    ]
    lines.extend(["", "## 본문", "", "```", build_newsletter_md(stamp, summary, insights), "```"])
    return "\n".join(lines)


def _cta_html(insights: list[Insight]) -> str:
    topic = _nl_label(_newsletter_title(insights[0]) if insights else "AX", 28)
    return (
        f"<p style='margin:0 0 12px;'>팀 반복 업무 3개를 적고, 그중 1개만 "
        f"<strong>{html.escape(topic)}</strong> 관점으로 자동화 후보를 골라보세요.</p>"
        "<p style='margin:0;'><a href='#' style='color:#E60012;font-weight:600;'>"
        "→ 통합 컨텍스트에서 전문 확인 (링크 1곳)</a></p>"
    )


def assemble_newsletter(stamp: str, brief_text: str) -> tuple[Path, Path, Path, Path]:
    cfg = load_newsletter_config()
    summary, insights = parse_brief(brief_text)
    summary = humanize(summary, genre="blog").text
    slug = slugify(_newsletter_title(insights[0]) if insights else "weekly")
    topic = _newsletter_title(insights[0]) if insights else "AI 마케팅 주간"
    ranked = _ranked_subjects(topic, stamp, cfg)
    winner = ranked[0] if ranked else None
    pre = _preheader(summary, cfg)
    tldr = _tldr_bullets(insights)
    hero = _hero_block(insights[0] if insights else None, summary)
    grab = _grab_bag(insights).replace("📊 **한 줄 데이터** — ", "")
    teaser = _next_teaser(insights).replace("**다음 호 예고:** ", "")

    nl_dir = WORKDIR / "content" / "newsletter"
    pkg_dir = WORKDIR / "content" / "packages"
    nl_dir.mkdir(parents=True, exist_ok=True)
    pkg_dir.mkdir(parents=True, exist_ok=True)
    nl_path = nl_dir / f"{stamp}_newsletter_{slug}.md"
    html_path = nl_dir / f"{stamp}_newsletter_{slug}.html"
    ctx_path = pkg_dir / f"{stamp}_newsletter-context.md"
    nl_path.write_text(build_newsletter_md(stamp, summary, insights), encoding="utf-8")
    ctx_path.write_text(build_newsletter_context_md(stamp, summary, insights), encoding="utf-8")
    html_path.write_text(
        build_newsletter_html(
            stamp,
            preheader=pre,
            winner=winner,
            tldr=tldr,
            hero=hero,
            insights=insights,
            grab_bag=grab,
            cta_html=_cta_html(insights),
            teaser=teaser,
        ),
        encoding="utf-8",
    )
    save_subject_scores(stamp, ranked, cfg)
    from lib.newsletter_paste import write_paste_pack

    paste_path = write_paste_pack(stamp, nl_path=nl_path, html_path=html_path, brief_text=brief_text)
    patch_unified_context_newsletter(stamp, ranked, nl_path, html_path, ctx_path, paste_path)
    return nl_path, ctx_path, html_path, paste_path
