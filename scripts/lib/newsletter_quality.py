"""B2B 뉴스레터 — 오픈율·완독율(CTOR) 최적화 결정적 생성."""
from __future__ import annotations

import html
import re
from pathlib import Path

import yaml

from lib.common import compress_sentences, finish_at_sentence, slugify
from lib.content_quality import Insight, parse_brief, polish_display_title, is_garbage_korean_title
from lib.humanize_korean import humanize
from lib.newsletter_html import build_newsletter_html
from lib.newsletter_issue_ledger import append_issue
from lib.newsletter_select import (
    SelectedIssue,
    display_title_for,
    select_issue_insights,
)
from lib.newsletter_subject import (
    format_subject_ab_block,
    rank_subjects,
    save_subject_scores,
)

WORKDIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = WORKDIR / "config" / "newsletter.yaml"


def load_newsletter_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _nl_short(text: str, max_chars: int, *, max_sentences: int = 2) -> str:
    """완결 문장만 — 중간 '…' 생략 금지."""
    return compress_sentences((text or "").strip(), max_chars, max_sentences=max_sentences)


def _newsletter_title(ins: Insight, cfg: dict | None = None) -> str:
    """뉴스레터용 완결 제목 — source_title 정합 우선, 정적 AX 폴백 금지."""
    return display_title_for(ins, cfg or load_newsletter_config())


def _nl_label(text: str, max_chars: int) -> str:
    """인라인 제목·라벨 — polish 후 완결 문장 압축."""
    return _nl_short(polish_display_title(text or ""), max_chars, max_sentences=1)


def _pick_apply(ins: Insight) -> str:
    for field in (ins.utilization, ins.marketer_view, ins.guides_tips, ins.insight_derivation):
        val = (field or "").strip()
        if len(val) >= 20:
            return val
    return "실무 체크리스트와 사례 검증으로 팀 내 도입 우선순위를 정해 보세요."


def _subject_topic_label(topic: str, max_chars: int = 28) -> str:
    """제목 템플릿용 — 단어 경계에서 자르기."""
    t = re.sub(r"\s+", " ", (topic or "").strip())
    if len(t) <= max_chars:
        return t
    cut = t[:max_chars]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    elif "—" in cut:
        cut = cut.rsplit("—", 1)[0].rstrip()
    elif "-" in cut:
        cut = cut.rsplit("-", 1)[0].rstrip()
    return cut.rstrip(" ,·/") or t[:max_chars]


def _subject_candidates(topic: str, stamp: str, cfg: dict | None = None, selected: SelectedIssue | None = None) -> list[str]:
    """패턴 로테이션 후보 — SelectedIssue 우선."""
    if selected and selected.subject_candidates:
        return list(selected.subject_candidates)
    c = cfg or load_newsletter_config()
    from lib.newsletter_subject import subject_limits

    max_c, _, _ = subject_limits(c)
    t = _subject_topic_label(topic, 28)
    templates = [p.get("template") for p in (c.get("subject_patterns") or []) if p.get("template")]
    if not templates:
        templates = c.get("subject_templates") or [
            "{topic} — 지금 손댈 곳은?",
            "{topic}, 3분이면 돼요",
            "[{stamp}] B2B AI 주간 신호",
        ]
    out: list[str] = []
    for tpl in templates:
        cand = str(tpl).format(topic=t, stamp=stamp)
        if len(cand) <= max_c:
            out.append(cand)
        else:
            out.append(finish_at_sentence(cand, max_c))
        if len(out) >= 3:
            break
    return out


def _preheader(summary: str, cfg: dict | None = None) -> str:
    from lib.newsletter_prose import scrub_phrase

    c = cfg or load_newsletter_config()
    max_c = int((c.get("benchmarks") or {}).get("preheader_max_chars", 40))
    fallback = "Top 3만 골라도 이번 주 실무가 움직여요."
    s = humanize(summary, genre="linkedin").text.replace("\n", " ")
    s = scrub_phrase(s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^일일 관측\([^)]+\)\s*—\s*", "", s)
    # Brief 메타/보일러플레이트면 대체
    if (
        not s
        or "교차 신호" in s
        or "재해석할 여지" in s
        or re.search(r"Top\s*\d+|축은|관측\(", s)
    ):
        return fallback[:max_c]
    out = finish_at_sentence(s, max_c)
    if len(out) > max_c:
        out = finish_at_sentence(_nl_short(s, max_c, max_sentences=1), max_c)
    out = (out or "").strip(" `.—,-· ")
    if not out or "교차 신호" in out or len(out) < 12 or out.endswith((",", "·", "—")):
        return fallback[:max_c]
    return out


def _tldr_bullets(insights: list[Insight], cfg: dict | None = None) -> list[str]:
    from lib.longform_context import complete_text, load_longform_config
    from lib.newsletter_prose import unique_sentences

    c = cfg or load_newsletter_config()
    lcfg = load_longform_config()
    nc = lcfg.get("newsletter") or {}
    bullets: list[str] = []
    for ins in insights[:3]:
        title = _nl_label(_newsletter_title(ins, c), 40).rstrip(".")
        title = unique_sentences(title, max_sentences=1) or title
        if "실무 인사이트" in title and title.startswith("2026"):
            title = _newsletter_title(ins, c)
            title = _nl_label(title, 40).rstrip(".")
            if "실무 인사이트" in title:
                title = "이번 주 B2B AI 실무 신호"
        body = unique_sentences(
            complete_text(
                ins.korean_summary or ins.insight_derivation or ins.marketer_view or "",
                int(nc.get("tldr_body_max_chars", 120)),
                max_sentences=int(nc.get("tldr_bullet_sentences", 2)),
                cfg=lcfg,
            ),
            max_sentences=2,
        )
        bullets.append(f"**{title}** — {body}")
    while len(bullets) < 3:
        bullets.append("이번 주 AX·AEO·에이전트 신호를 3분 안에 정리했어요.")
    return bullets


def _hero_block(ins: Insight | None, summary: str, cfg: dict | None = None) -> str:
    from lib.content_quality import expand_insight_body
    from lib.longform_context import complete_text, load_longform_config
    from lib.newsletter_prose import densify_hero_parts, scrub_apply

    c = cfg or load_newsletter_config()
    lcfg = load_longform_config()
    nc = lcfg.get("newsletter") or {}
    if not ins:
        from lib.newsletter_prose import unique_sentences

        return unique_sentences(
            humanize(
                complete_text(summary, 420, max_sentences=int(nc.get("hero_sentences", 5)), cfg=lcfg),
                genre="linkedin",
            ).text,
            max_sentences=5,
        )
    title = _newsletter_title(ins, c)
    problem = complete_text(ins.marketer_view or summary, 220, max_sentences=3, cfg=lcfg)
    explanation = complete_text(expand_insight_body(ins, 1), 320, max_sentences=4, cfg=lcfg)
    insight = complete_text(
        ins.insight_derivation or ins.korean_summary or "",
        200,
        max_sentences=2,
        cfg=lcfg,
    )
    apply = scrub_apply(complete_text(_pick_apply(ins), 160, max_sentences=2, cfg=lcfg))
    return densify_hero_parts(
        title=title,
        problem=problem,
        explanation=explanation,
        insight=insight,
        apply=apply,
    )


def _insight_module(idx: int, ins: Insight, cfg: dict | None = None) -> str:
    """Morning Brew: 볼드 헤드라인 + problem→explanation→insight→apply."""
    from lib.content_quality import expand_insight_body
    from lib.longform_context import complete_text, load_longform_config
    from lib.newsletter_prose import scrub_apply, unique_sentences

    c = cfg or load_newsletter_config()
    lcfg = load_longform_config()
    headline = _newsletter_title(ins, c)
    used: list[str] = []
    problem = unique_sentences(
        humanize(
            complete_text(ins.marketer_view or ins.summary or "", 200, max_sentences=3, cfg=lcfg),
            genre="linkedin",
        ).text,
        max_sentences=2,
        against=used,
    )
    if problem:
        used.append(problem)
    explanation = unique_sentences(
        humanize(expand_insight_body(ins, idx), genre="linkedin").text,
        max_sentences=3,
        against=used,
    )
    if explanation:
        used.append(explanation)
    insight = unique_sentences(
        humanize(
            complete_text(
                ins.insight_derivation or ins.korea_apply or ins.korean_summary or "",
                220,
                max_sentences=3,
                cfg=lcfg,
            ),
            genre="linkedin",
        ).text,
        max_sentences=2,
        against=used,
    )
    # 인사이트가 문제/설명과 전부 겹치면 다른 필드·폴백으로 채움
    if not insight:
        insight = unique_sentences(
            ins.korea_apply or ins.guides_tips or "",
            max_sentences=1,
            against=used,
        )
    if not insight:
        insight = "같은 신호가라도, 오늘 실험 단위를 하나만 고르면 실행이 빨라져요."
    apply = scrub_apply(
        humanize(
            complete_text(_pick_apply(ins), 180, max_sentences=3, cfg=lcfg),
            genre="linkedin",
        ).text
    )
    # 적용이 설명/문제와 과도하게 겹치면 짧은 실행문
    from lib.newsletter_prose import sentence_similar

    if apply and any(sentence_similar(apply, u, threshold=0.75) for u in used):
        apply = "오늘 캘린더에 실험 1건만 넣고, 지표 1개로 결과를 남기세요."
    src = ins.url or "—"
    return "\n".join(
        [
            f"### {idx}. **{headline}**",
            "",
            f"**문제:** {problem}",
            "",
            f"**설명:** {explanation or '맥락 신호는 위 문제에 연결된 실행 단위로 쪼개 보세요.'}",
            "",
            f"**인사이트:** {insight}",
            "",
            f"- **현장 적용:** {apply}",
            f"- **출처:** {src}",
        ]
    )


def _ranked_subjects(topic: str, stamp: str, cfg: dict | None = None, selected: SelectedIssue | None = None):
    c = cfg or load_newsletter_config()
    return rank_subjects(_subject_candidates(topic, stamp, c, selected), c)


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


def build_newsletter_md(
    stamp: str,
    summary: str,
    insights: list[Insight],
    *,
    selected: SelectedIssue | None = None,
) -> str:
    """완독율 중심 모듈형 뉴스레터 본문."""
    cfg = load_newsletter_config()
    sel = selected or select_issue_insights(stamp, insights, cfg)
    picked = sel.insights
    topic = sel.topic
    ranked = _ranked_subjects(topic, stamp, cfg, sel)
    pre = _preheader(summary, cfg)
    ctor = (cfg.get("benchmarks") or {}).get("ctor_target", "10-15%")
    send = cfg.get("send_window") or {}
    send_note = send.get("time_kst", "10:00-11:00 KST")
    tldr = _tldr_bullets(picked, cfg)
    hero = _hero_block(sel.hero, summary, cfg)
    modules = [_insight_module(i, ins, cfg) for i, ins in enumerate(picked[:3], 1)]

    lines = [
        f"# 주간 AI·AX 뉴스레터 — {stamp}",
        "",
        "## 발송 메타 (오픈율)",
        "",
        f"- **발신:** Hermes Studio (개인명 발신 권장 — Stripo +4~57% opens)",
        f"- **권장 발송:** {send_note} (B2B sweet spot)",
        f"- **선별 패턴:** {sel.pattern_id}",
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
            "## 타이틀 이미지 (16:9)",
            "",
            f"<!-- TITLE_IMAGE_16x9 -->",
            f"프롬프트: `content/newsletter/{stamp}_title-image-16x9.md`",
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
            "*(모듈형 · problem → explanation → insight → apply)*",
            "",
            *modules,
            "",
            "---",
            "",
            _grab_bag(picked),
            "",
            "---",
            "",
            "## 실무 프레임 (earn scroll)",
            "",
            _practice_frame(picked, cfg),
            "",
            "---",
            "",
            *_single_cta(picked, cfg, stamp=stamp).splitlines(),
            "",
            "---",
            "",
            "## 다음 호",
            "",
            _next_teaser(picked, cfg),
            "",
            "---",
            "",
            "## 품질 메모",
            "",
            f"- KPI: **CTOR {ctor}** 우선 (오픈율은 MPP 보정 후 방향성만)",
            "- 구조: TLDR → Hero → 3모듈 → 단일 CTA ([Stripo 2026](https://research.stripo.email/b2b-email-open-rate-benchmarks-2026))",
            "- 레이아웃: 모바일 단일 컬럼 · 링크 1곳 ([Morning Brew modular](https://growthmodels.co/morning-brew-marketing/))",
            f"- LinkedIn 장문: `content/linkedin/{stamp}_newsletter-article.md`",
        ]
    )
    return "\n".join(lines)


def build_newsletter_context_md(
    stamp: str,
    summary: str,
    insights: list[Insight],
    *,
    selected: SelectedIssue | None = None,
) -> str:
    """Notion/에디터용 컨텍스트 패키지."""
    cfg = load_newsletter_config()
    sel = selected or select_issue_insights(stamp, insights, cfg)
    topic = sel.topic
    ranked = _ranked_subjects(topic, stamp, cfg, sel)
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
    lines.extend(
        [
            "",
            "## 본문",
            "",
            "```",
            build_newsletter_md(stamp, summary, insights, selected=sel),
            "```",
        ]
    )
    return "\n".join(lines)


def _grab_bag(insights: list[Insight]) -> str:
    from lib.newsletter_prose import unique_sentences

    ins = insights[0] if insights else None
    line = ""
    if ins and ins.market_impact:
        line = unique_sentences(ins.market_impact, max_sentences=2)
    if not line or "Direct Answer" in line or "교차 신호" in line:
        line = "Answer Engine·GEO 투자는 SEO와 분리되지 않습니다."
    return (
        f"📊 **한 줄 데이터** — {line} "
        "벤치마크 감각: B2B CTOR 10–15%면 링크·실험 설계가 건강한 편이에요."
    )


def _practice_frame(insights: list[Insight], cfg: dict | None = None) -> str:
    """Earn-scroll 섹션 — 짧고 밀도 높은 체크리스트 (모듈 복붙 금지)."""
    from lib.newsletter_prose import scrub_apply, unique_sentences

    c = cfg or load_newsletter_config()
    parts: list[str] = [
        "한 호에서 기억할 프레임은 **문제 → 설명 → 인사이트 → 현장 적용**이에요.",
        "스킵 독자는 TLDR만, 완독 독자는 아래 한 줄 액션만 가져가면 됩니다.",
        "오픈율은 제목·프리헤더가, 클릭률은 이 액션 한 줄과 CTA 한 곳이 결정합니다.",
        "",
    ]
    for i, ins in enumerate(insights[:3], 1):
        title = _newsletter_title(ins, c)
        action = scrub_apply(ins.utilization or ins.guides_tips or ins.marketer_view or "")
        tip = unique_sentences(
            ins.insight_derivation or ins.korea_apply or "",
            max_sentences=1,
            against=[action],
        )
        why = unique_sentences(
            ins.market_impact or ins.opportunity or "",
            max_sentences=1,
            against=[action, tip],
        )
        line = f"**{i}. {title}** — {action}"
        if tip and tip not in action:
            line = f"{line} ({tip})"
        if why and why not in line:
            line = f"{line} / 왜: {why}"
        parts.append(line)
        parts.append("")
    parts.append(
        "다음 호로 넘기기 전에, 위 3개 중 **오늘 실행할 1개**만 캘린더에 넣고 CTA 링크에서 근거를 확인하세요."
    )
    parts.append(
        "측정은 오픈이 아니라 클릭·회신·실험 완료 여부입니다. 한 주의 학습 루프를 닫는 게 CTOR의 실체예요."
    )
    parts.append("회신 한 줄이면 다음 호 A/B 제목 가설을 더 날카롭게 다듬을 수 있어요.")
    return "\n".join(parts).strip()


def _single_cta(insights: list[Insight], cfg: dict | None = None, *, stamp: str = "") -> str:
    from lib.newsletter_cta import build_cta, render_cta_markdown

    c = cfg or load_newsletter_config()
    topic = _nl_label(_newsletter_title(insights[0], c) if insights else "AX", 28)
    cta = build_cta(insights[0] if insights else None, stamp or "1970-01-01", c)
    return render_cta_markdown(cta, topic)


def _next_teaser(insights: list[Insight], cfg: dict | None = None) -> str:
    c = cfg or load_newsletter_config()
    nxt = _nl_label(
        _newsletter_title(insights[1], c) if len(insights) > 1 else "LLM 4사 주간 펄스",
        48,
    )
    return (
        f"**다음 호 예고:** {nxt} — 심화 FAQ와 체크리스트로 이어갑니다. "
        "이번 호에서 고른 액션 1개의 결과를 메모해 두면, 다음 호 실험 설계가 빨라집니다."
    )

def _cta_html(insights: list[Insight], cfg: dict | None = None, *, stamp: str = "") -> str:
    from lib.newsletter_cta import build_cta, render_cta_html

    c = cfg or load_newsletter_config()
    topic = _nl_label(_newsletter_title(insights[0], c) if insights else "AX", 28)
    cta = build_cta(insights[0] if insights else None, stamp or "1970-01-01", c)
    return render_cta_html(cta, topic)


def _prune_stale_issues(nl_dir: Path, stamp: str, keep: set[Path]) -> list[Path]:
    """같은 날짜 재생성 시 주제(slug)가 바뀌면 남는 구버전 호 제거.

    Notion `newsletter_html` glob이 `*_newsletter_*.html`이라 방치하면 구버전이
    함께 아카이브되고, eval 스크립트도 엉뚱한 파일을 검사한다.
    """
    removed: list[Path] = []
    for ext in ("md", "html"):
        for path in nl_dir.glob(f"{stamp}_newsletter_*.{ext}"):
            if path in keep or "subject-scores" in path.name:
                continue
            try:
                path.unlink()
                removed.append(path)
            except OSError:
                continue
    return removed


def assemble_newsletter(stamp: str, brief_text: str) -> tuple[Path, Path, Path, Path]:
    cfg = load_newsletter_config()
    summary, insights = parse_brief(brief_text)
    summary = humanize(summary, genre="blog").text
    selected = select_issue_insights(stamp, insights, cfg)
    picked = selected.insights
    slug = slugify(selected.topic or "weekly")
    topic = selected.topic
    ranked = _ranked_subjects(topic, stamp, cfg, selected)
    winner = ranked[0] if ranked else None
    pre = _preheader(summary, cfg)
    tldr = _tldr_bullets(picked, cfg)
    hero = _hero_block(selected.hero, summary, cfg)
    grab = _grab_bag(picked).replace("📊 **한 줄 데이터** — ", "")
    teaser = _next_teaser(picked, cfg).replace("**다음 호 예고:** ", "")

    nl_dir = WORKDIR / "content" / "newsletter"
    pkg_dir = WORKDIR / "content" / "packages"
    nl_dir.mkdir(parents=True, exist_ok=True)
    pkg_dir.mkdir(parents=True, exist_ok=True)
    nl_path = nl_dir / f"{stamp}_newsletter_{slug}.md"
    html_path = nl_dir / f"{stamp}_newsletter_{slug}.html"
    ctx_path = pkg_dir / f"{stamp}_newsletter-context.md"
    _prune_stale_issues(nl_dir, stamp, keep={nl_path, html_path})
    nl_body = build_newsletter_md(stamp, summary, insights, selected=selected)
    nl_path.write_text(nl_body, encoding="utf-8")
    ctx_path.write_text(
        build_newsletter_context_md(stamp, summary, insights, selected=selected),
        encoding="utf-8",
    )
    html_path.write_text(
        build_newsletter_html(
            stamp,
            preheader=pre,
            winner=winner,
            tldr=tldr,
            hero=hero,
            insights=picked,
            grab_bag=grab,
            cta_html=_cta_html(picked, cfg, stamp=stamp),
            teaser=teaser,
        ),
        encoding="utf-8",
    )
    save_subject_scores(stamp, ranked, cfg)

    from lib.newsletter_image_prompt import write_title_image_prompt
    from lib.newsletter_linkedin import write_linkedin_article
    from lib.newsletter_paste import write_paste_pack

    img_path = write_title_image_prompt(stamp, selected, cfg)
    li_path = write_linkedin_article(stamp, selected, summary, cfg)
    paste_path = write_paste_pack(
        stamp,
        nl_path=nl_path,
        html_path=html_path,
        brief_text=brief_text,
        linkedin_path=li_path,
        image_prompt_path=img_path,
        selected=selected,
    )
    patch_unified_context_newsletter(stamp, ranked, nl_path, html_path, ctx_path, paste_path)

    append_issue(
        stamp,
        topic=topic,
        subject=(winner.text if winner else topic),
        pattern_id=selected.pattern_id,
        urls=[i.url for i in picked],
        hero=hero,
        reasons=selected.reasons,
        cfg=cfg,
    )
    from lib.newsletter_gates import write_publish_status

    write_publish_status(stamp, cfg)
    return nl_path, ctx_path, html_path, paste_path
