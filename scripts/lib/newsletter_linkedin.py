"""LinkedIn 뉴스레터 장문 — 이메일과 동일 논지, 별도 원고 (결정적)."""
from __future__ import annotations

from pathlib import Path

from lib.content_quality import Insight, expand_insight_body
from lib.humanize_korean import humanize
from lib.longform_context import complete_text, load_longform_config
from lib.newsletter_cta import build_cta
from lib.newsletter_select import SelectedIssue, display_title_for

WORKDIR = Path(__file__).resolve().parents[2]


def _word_count(text: str) -> int:
    """한국어·영문 혼합 어절 근사치."""
    return len([t for t in (text or "").replace("\n", " ").split(" ") if t.strip()])


def _para(text: str, max_chars: int = 420, sentences: int = 4) -> str:
    cfg = load_longform_config()
    raw = complete_text(text, max_chars, max_sentences=sentences, cfg=cfg)
    return humanize(raw, genre="linkedin").text.replace("맥롽", "맥락")


def build_linkedin_article_md(
    stamp: str,
    selected: SelectedIssue,
    summary: str,
    cfg: dict | None = None,
) -> str:
    c = cfg or {}
    topic = selected.topic
    insights = selected.insights
    hero = selected.hero
    cta = build_cta(hero, stamp, c)
    alt = f"{topic} 주간 뉴스레터 타이틀 이미지"

    hook_src = hero.insight_derivation or hero.marketer_view or summary
    hook = _para(
        f"{topic} — 많은 팀이 도구부터 고르지만, 실제 병목은 '{hook_src}'에서 드러납니다.",
        280,
        3,
    )

    problem = _para(
        hero.marketer_view or hero.summary or summary,
        500,
        5,
    )
    explanation = _para(expand_insight_body(hero, 1), 560, 6)
    insight = _para(
        hero.insight_derivation or hero.korea_apply or hero.korean_summary,
        480,
        5,
    )
    apply = _para(
        hero.utilization or hero.guides_tips or "체크리스트로 우선순위 1개를 고르세요.",
        360,
        4,
    )

    module_sections: list[str] = []
    for i, ins in enumerate(insights[:3], 1):
        title = display_title_for(ins, c)
        body = _para(expand_insight_body(ins, i), 520, 5)
        tip = _para(ins.utilization or ins.guides_tips or ins.marketer_view or "", 240, 3)
        src = ins.url if (ins.url or "").startswith("https://") else "—"
        module_sections.extend(
            [
                f"## {i}. {title}",
                "",
                body,
                "",
                f"**바로 적용:** {tip}",
                "",
                f"출처: {src}",
                "",
            ]
        )

    cta_block = (
        f"[{cta.label}]({cta.url})"
        if cta.ok
        else "발행 전 https CTA URL을 연결하세요."
    )

    lines = [
        f"# {topic}",
        "",
        f"**LinkedIn Newsletter · {stamp} · Hermes Studio**",
        "",
        f"![타이틀 이미지 16:9 — {alt}](./{stamp}_title-image-16x9.md)",
        f"*{alt}*",
        "",
        "---",
        "",
        hook,
        "",
        "## 왜 지금인가",
        "",
        problem,
        "",
        "## 무엇이 바뀌고 있나",
        "",
        explanation,
        "",
        "## 한 줄 인사이트",
        "",
        insight,
        "",
        "## 실무에서 이렇게",
        "",
        apply,
        "",
        *module_sections,
        "## 심화 체크리스트",
        "",
        _para(
            f"{topic} 기준으로 ① 현황 1페이지 ② FAQ 5개 ③ 파일럿 지표 3개를 이번 주에 만드세요. "
            f"측정 없는 도입은 비용만 늘립니다. {hero.guides_tips or hero.opportunity or ''}",
            520,
            5,
        ),
        "",
        "## 팀 대화용 질문",
        "",
        _para(
            f"우리 팀에서 {topic}이 막히는 지점은 도구·데이터·승인·역량 중 어디인가요. "
            f"한 가지만 고르면 다음 액션이 분명해집니다. {hero.korea_apply or hero.market_impact or ''}",
            480,
            5,
        ),
        "",
        "## 이번 주 한 가지 요청",
        "",
        f"팀에서 **{topic}** 기준으로 반복 업무 1개만 골라 자동화 후보로 적어 보세요.",
        "",
        cta_block,
        "",
        "댓글로 막히는 지점을 남겨 주시면 다음 호에 반영할게요.",
        "",
        "---",
        "",
        f"*이미지 프롬프트:* `content/newsletter/{stamp}_title-image-16x9.md`",
    ]
    body = "\n".join(lines)
    # Ensure LinkedIn band (800+) with deterministic expansion from remaining insights
    guard = 0
    while _word_count(body) < 820 and insights and guard < 3:
        guard += 1
        idx = min(guard, len(insights) - 1)
        extra = _para(expand_insight_body(insights[idx], idx + 1), 780, 8)
        title = display_title_for(insights[idx], c)
        body = body.replace(
            "## 이번 주 한 가지 요청",
            f"## 심화 노트 {guard}: {title}\n\n{extra}\n\n## 이번 주 한 가지 요청",
            1,
        )
    if _word_count(body) < 820:
        filler = _para(
            f"{topic}을 팀 워크숍 주제로 쓰면, 참가자는 사례·반대 의견·다음 실험을 같은 템플릿으로 정리할 수 있어요. "
            f"이메일은 짧게 열고 LinkedIn 장문으로 근거를 남기는 구조가 CTOR과 회신율을 함께 올립니다. "
            f"{hero.opportunity or hero.market_impact or hero.korea_apply or ''}",
            700,
            7,
        )
        body = body.replace(
            "## 이번 주 한 가지 요청",
            f"## 발행 운영 메모\n\n{filler}\n\n## 이번 주 한 가지 요청",
            1,
        )
    return body


def write_linkedin_article(
    stamp: str,
    selected: SelectedIssue,
    summary: str,
    cfg: dict | None = None,
) -> Path:
    out_dir = WORKDIR / "content" / "linkedin"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{stamp}_newsletter-article.md"
    # ensure image prompt exists for cross-link
    from lib.newsletter_image_prompt import write_title_image_prompt

    write_title_image_prompt(stamp, selected, cfg)
    path.write_text(build_linkedin_article_md(stamp, selected, summary, cfg), encoding="utf-8")
    return path


def linkedin_length_ok(text: str, *, lo: int = 800, hi: int = 1500) -> bool:
    n = _word_count(text)
    return lo <= n <= hi + 200  # slight tolerance for Korean eojul variance
