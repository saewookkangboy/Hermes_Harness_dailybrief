"""Hermes Content Studio — 품질 중심 콘텐츠 생성 엔진."""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.common import compress_sentences, finish_at_sentence, read_template, slugify, truncate
from lib.humanize_korean import humanize, humanize_linkedin_post

WORKDIR = Path.home() / "hermes-content-studio"


@dataclass
class Insight:
    title: str
    summary: str
    marketer_view: str
    channels: str
    url: str
    market_impact: str = ""
    korea_apply: str = ""
    opportunity: str = ""
    insight_derivation: str = ""
    utilization: str = ""
    guides_tips: str = ""
    research_category: str = ""

    @property
    def korean_title(self) -> str:
        return polish_display_title(self.title)

    @property
    def korean_summary(self) -> str:
        return synthesize_korean_summary(self.title, self.summary, self.marketer_view)

    def context_blurb(self, *, max_chars: int = 220, max_sentences: int = 2) -> str:
        """Unified·Research 표용 — 완결 문장 맥락 요약."""
        parts: list[str] = []
        for field in (self.insight_derivation, self.marketer_view):
            val = (field or "").strip()
            if val and has_meaningful_korean(val) and val not in parts:
                parts.append(val)
        if not parts:
            summary = (self.summary or "").strip()
            if summary and has_meaningful_korean(summary):
                parts.append(summary)
        text = " ".join(parts) if parts else self.korean_summary
        return compress_sentences(text, max_chars, max_sentences=max_sentences)


def _hangul_count(text: str) -> int:
    return len(re.findall(r"[가-힣]", text or ""))


def has_meaningful_korean(text: str, *, min_chars: int = 4) -> bool:
    return _hangul_count(text) >= min_chars


def is_garbage_korean_title(title: str) -> bool:
    """영문 조각 + '실무 가이드' 등 다운스트림 맥락 단절 제목."""
    t = (title or "").strip()
    if not t:
        return True
    latin = len(re.findall(r"[A-Za-z]", t))
    hangul = _hangul_count(t)
    if "..." in t or "…" in t:
        return True
    if hangul < 8 and latin > 12:
        return True
    if re.search(r" — 실무\s*가이드\s*$", t) and latin > 10:
        return True
    return False


def localize_title(title: str) -> str:
    """영문 제목을 한국어 실무 제목으로 변환 (규칙 기반 · 완결형)."""
    t = title.strip()
    tl = t.lower()

    if has_meaningful_korean(t) and not is_garbage_korean_title(t):
        return re.sub(r"\s+", " ", t).strip()

    if "ax" in tl and ("korea" in tl or "south korea" in tl):
        return "한국 AX 전환, 지금 시작해야 하는 이유"
    if "aeo" in tl or "answer engine" in tl or "ai search" in tl:
        return "2026 AEO(Answer Engine Optimization) 실무 가이드"
    if "agent" in tl and "automation" in tl:
        return "AI 에이전트 자동화, 2026 워크플로 혁신"
    if "workspace agent" in tl or "chatgpt workspace" in tl:
        return "ChatGPT Workspace Agents 실무 검토"
    if "cursor" in tl or "windsurf" in tl:
        return "Cursor vs Windsurf — 2026 AI IDE 선택 가이드"
    if "expo" in tl or "axia" in tl:
        return "AXIA EXPO 2026 — 국내 AX 실무 신호"
    if "marketing" in tl and "asia" in tl:
        return "아시아 디지털 마케팅 2026 트렌드"
    if "release notes" in tl or "help.openai" in tl:
        return "ChatGPT 릴리스 노트 주간 펄스"
    if "opus" in tl or ("anthropic" in tl and "claude" in tl):
        return "Claude Opus 업데이트 — 엔터프라이즈 적용"
    if "enterprise ai adoption" in tl or "pilots to production" in tl:
        return "엔터프라이즈 AI 도입 — 파일럿에서 프로덕션으로"
    if "developer" in tl and "openai" in tl:
        return "OpenAI 개발자 커뮤니티 동향"
    if "sk telecom" in tl or "nvidia" in tl:
        return "SK텔레콤·NVIDIA AI 인프라 협력"
    if "perplexity" in tl:
        return "Perplexity·AI 검색(AEO) 최적화 실무"
    if "gemini" in tl:
        return "Google Gemini 업데이트 — AEO·Workspace 연동"

    keywords = []
    for kw, label in [
        ("aeo", "AEO"),
        ("agent", "AI 에이전트"),
        ("automation", "자동화"),
        ("marketing", "마케팅"),
        ("seo", "SEO"),
    ]:
        if kw in tl:
            keywords.append(label)
    if keywords:
        return f"2026 {keywords[0]} 실무 인사이트"
    words = re.sub(r"[^\w\s\-]", " ", t).split()[:5]
    if words:
        return compress_sentences(f"{' '.join(words)} 관련 AI·마케팅 신호입니다.", 72, max_sentences=1)
    return "2026 AI·마케팅 실무 인사이트"


def polish_display_title(title: str) -> str:
    """브리프·Unified에 노출할 완결형 제목."""
    t = (title or "").strip()
    if t and has_meaningful_korean(t) and not is_garbage_korean_title(t):
        return re.sub(r"\s+", " ", t).strip()
    return localize_title(t)


def synthesize_korean_summary(title: str, summary: str, marketer_view: str) -> str:
    """영문 스니펫을 한국어 실무 요약으로 재구성."""
    base = marketer_view.strip() if marketer_view else ""
    if base and has_meaningful_korean(base):
        return compress_sentences(base, 280, max_sentences=3)
    if summary and has_meaningful_korean(summary):
        return compress_sentences(summary, 280, max_sentences=3)
    tl = title.lower()
    if "aeo" in tl or "answer engine" in tl:
        return (
            "AI 검색(ChatGPT·Perplexity·Gemini)에서 브랜드가 인용되려면 "
            "FAQ 구조화, 직접 답변형 문단, 출처 명시가 꼭 필요해요. "
            "기존 SEO는 유지하면서 구조화 데이터와 신선도 신호만 강화해 보세요."
        )
    if "agent" in tl or "automation" in tl:
        return (
            "AI 에이전트는 단순 자동화를 넘어 LLM 오케스트레이션 기반 "
            "자율 태스크 실행 쪽으로 빠르게 바뀌고 있어요. 마케팅·운영 파이프라인에 "
            "에이전트 워크플로를 단계적으로 넣는 게 2026년 핵심 과제예요."
        )
    if "ax" in tl or "korea" in tl or "transformation" in tl:
        return (
            "한국 기업의 AX(AI Transformation) 전환은 교육·컨설팅·내부 "
            "자동화 도입 수요로 이어지고 있어요. B2B 콘텐츠·강의·"
            "실습 자료로 전환 로드맵을 보여주면 수요에 잘 맞아요."
        )
    if "cursor" in tl or "windsurf" in tl or "ide" in tl:
        return (
            "AI IDE(Cursor·Windsurf)는 Agent 모드와 Background Agent로 "
            "코딩 워크플로를 재편하고 있어요. 개발자·마케터 모두 "
            "바이브 코딩 역량이 콘텐츠·자동화 생산성의 차별점이 돼요."
        )
    if "workspace" in tl or "chatgpt" in tl:
        return (
            "ChatGPT Workspace Agents는 팀 협업 맥락에서 AI 에이전트를 "
            "실험할 수 있는 신호예요. Pro 플랜 한계와 실무 적용 갭을 "
            "직접 검증한 뒤 콘텐츠·교육 소재로 써 보세요."
        )
    return (
        f"{localize_title(title)} 관련 트렌드는 B2B 마케팅·AX 교육 콘텐츠로 "
        "재가공하기 좋아요. 글로벌 사례를 국내 실무 맥락에 맞게 해석해 "
        "FAQ형 블로그와 소셜 캐러셀로 확장해 보세요."
    )


def parse_brief(text: str) -> tuple[str, list[Insight]]:
    summary_m = re.search(r"## Executive Summary\n(.+?)\n\n##", text, re.S)
    summary = summary_m.group(1).strip() if summary_m else "AI·마케팅·AX 주간 트렌드 요약"

    blocks = re.split(r"\n### \d+\. ", text)
    insights: list[Insight] = []
    for block in blocks[1:9]:
        title = block.split("\n", 1)[0].strip()
        url_m = re.search(r"- \*\*출처:\*\* (.+)", block)
        summary_m = re.search(r"- \*\*(?:내용 )?요약:\*\* (.+)", block)
        marketer_m = re.search(r"- \*\*마케터 관점:\*\* (.+)", block)
        channel_m = re.search(r"- \*\*콘텐츠 소재:\*\* (.+)", block)
        market_m = re.search(r"- \*\*시장 영향:\*\* (.+)", block)
        korea_m = re.search(r"- \*\*한국 적용:\*\* (.+)", block)
        opp_m = re.search(r"- \*\*기회:\*\* (.+)", block)
        insight_m = re.search(r"- \*\*Insight 도출:\*\* (.+)", block)
        util_m = re.search(r"- \*\*활용 방법:\*\* (.+)", block)
        guides_m = re.search(r"- \*\*가이드·팁:\*\* (.+)", block)
        cat_m = re.search(r"- \*\*리서치 영역:\*\* (.+)", block)
        ko_title_m = re.search(r"- \*\*한국어 제목:\*\* (.+)", block)
        ko_raw = ko_title_m.group(1).strip() if ko_title_m else ""
        display_title = ko_raw if ko_raw and not is_garbage_korean_title(ko_raw) else title
        raw_summary = (summary_m.group(1) if summary_m else title).strip()
        insights.append(
            Insight(
                title=display_title,
                summary=compress_sentences(raw_summary, 400, max_sentences=4),
                marketer_view=(marketer_m.group(1) if marketer_m else ""),
                channels=(channel_m.group(1) if channel_m else "blog"),
                url=(url_m.group(1).strip() if url_m else ""),
                market_impact=(market_m.group(1) if market_m else "")[:300],
                korea_apply=(korea_m.group(1) if korea_m else "")[:300],
                opportunity=(opp_m.group(1) if opp_m else "")[:300],
                insight_derivation=(insight_m.group(1) if insight_m else "")[:300],
                utilization=(util_m.group(1) if util_m else "")[:300],
                guides_tips=(guides_m.group(1) if guides_m else "")[:300],
                research_category=(cat_m.group(1) if cat_m else "")[:80],
            )
        )
    return summary, insights


def _insight_topic_key(ins: Insight) -> str:
    tl = ins.title.lower()
    if "anthropic" in tl or "claude" in tl:
        return "llm_anthropic"
    if "gemini" in tl:
        return "llm_google"
    if "perplexity" in tl:
        return "llm_perplexity"
    if "hermes" in tl or "nousresearch" in tl:
        return "hermes_agent"
    if "harness" in tl or "context engineering" in tl or "prompt engineering" in tl:
        return "harness_engineering"
    if "governance" in tl or "responsible ai" in tl:
        return "ai_governance"
    if "literacy" in tl or "training" in tl:
        return "ai_literacy"
    if "ax" in tl or "korea" in tl or "transformation" in tl:
        return "korea_ax"
    if "agent" in tl and ("marketing" in tl or "builder" in tl):
        return "agent_marketing"
    if "workspace" in tl or "chatgpt" in tl:
        return "workspace_agents"
    if "aeo" in tl or "answer engine" in tl:
        return "aeo"
    if "cursor" in tl or "windsurf" in tl or "ide" in tl:
        return "ai_ide"
    return "general"


def _korean_source_context(ins: Insight) -> str:
    """출처 영문 스니펫 제외 — 한국어 해석만 반환."""
    parts = [
        ins.summary.strip(),
        ins.insight_derivation.strip(),
        ins.marketer_view.strip(),
        ins.utilization.strip(),
        ins.korea_apply.strip(),
        ins.market_impact.strip(),
        ins.guides_tips.strip(),
    ]
    korean = [p for p in parts if p and has_meaningful_korean(p)]
    if korean:
        return compress_sentences(" ".join(korean), 600, max_sentences=5)
    return ins.korean_summary


def expand_insight_body(ins: Insight, index: int) -> str:
    """출처 요약·시장 영향·한국 적용을 바탕으로 본문 단락 확장 (출처 URL 제외)."""
    key = _insight_topic_key(ins)
    title = ins.korean_title
    ctx = _korean_source_context(ins)

    if key == "ax":
        return (
            f"{index}번째로 주목할 주제는 {title}입니다. "
            f"출처 분석에 따르면 한국 기업이 AX(AI Transformation) 전환 여정에 본격적으로 "
            f"들어서면서, 운영 전반에 AI를 통합하지 않으면 경쟁력과 혁신 속도에서 "
            f"뒤처질 수 있다는 메시지가 분명합니다. "
            f"{ctx} "
            f"B2B 구매·교육 의사결정은 '기술 도입 선언'보다 '우리 조직에 무엇이 바뀌는지' "
            f"설명하는 콘텐츠에 반응합니다. 따라서 PoC 성공 사례만 나열하기보다, "
            f"현장 직군별 FAQ·강의 모듈·컨설팅 진단 체크리스트로 AX 로드맵을 "
            f"쪼개서 보여주는 전략이 효과적입니다. "
            f"특히 검색(AEO)과 소셜(LinkedIn·Instagram)에서 동일한 Direct Answer를 "
            f"재가공하면 교육 리드와 브랜드 신뢰를 동시에 쌓을 수 있습니다. "
            f"AX는 단순히 'AI 도구를 샀다'는 선언이 아니라, 데이터·프로세스·"
            f"인력 역량이 함께 움직여야 성과가 납니다. 콘텐츠 팀은 임원용 "
            f"한 페이지 요약과 실무자용 10분 FAQ를 분리해 제공하면 "
            f"구매 여정 전체를 커버할 수 있습니다. "
            f"한국 시장에서는 regulation·보안·legacy system 이슈로 "
            f"속도가 글로벌보다 느린 경우가 많으므로, '왜 지금 시작해야 하는지' "
            f"타임라인을 함께 제시하는 것이 설득력을 높입니다."
        )

    if key == "agent_marketing":
        return (
            f"{index}번째 인사이트는 {title}입니다. "
            f"Reddit 마케팅 자동화 커뮤니티의 실무 비교 글은 2026년 'AI agent'라는 "
            f"라벨이 과장되어 쓰이고 있다는 점을 먼저 짚습니다. "
            f"핵심은 빌더·플랫폼 이름이 아니라, 마케팅 팀이 실제로 반복하는 "
            f"업무 단위에 맞는 use case를 정의하는 것입니다. "
            f"{ctx} "
            f"에이전시 운영 경험담에서 언급된 '2026년에 바꿀 것'—측정, SOP, 프롬프트 "
            f"표준화—를 먼저 정리한 뒤 도구를 고르는 순서가 실패율을 크게 줄입니다. "
            f"콘텐츠 제작 관점에서는 '5대 빌더 비교'보다 '우리 팀 반복 업무 3개 → "
            f"에이전트 후보 매핑' 형식의 실습형 글이 저장·공유율이 높습니다. "
            f"마케팅 자동화 범위를 넓히기 전에 CRM·이메일·리포팅 중 "
            f"하루 30분 이상 쓰는 업무부터 표준화해야 합니다. "
            f"에이전트는 '만능 비서'가 아니라 '특정 SOP 실행기'로 정의할 때 "
            f"ROI 측정이 가능합니다. 국내 팀은 영어권 튜토리얼을 그대로 "
            f"복붙하기보다 한국어 FAQ와 내부 예시 데이터로 재현 실습을 "
            f"제공하는 콘텐츠가 전환에 유리합니다."
        )

    if key == "workspace_agents":
        return (
            f"{index}번째로 살펴볼 주제는 {title}입니다. "
            f"ChatGPT Workspace Agents에 대한 현장 피드백은 '유망하지만 기대보다 "
            f"덜 똑똑하다'는 양극화된 반응을 보여줍니다. "
            f"Pro 플랜 한계, 팀 협업 맥락에서의 컨텍스트 손실, 단일 에이전트 대비 "
            f"복합 워크플로 처리 갭이 반복적으로 언급됩니다. "
            f"{ctx} "
            f"마케터·운영 리더는 '도입 선언' 전에 2주 파일럿으로 기대치를 검증하고, "
            f"그 결과를 교육·블로그·LinkedIn 포스트로 투명하게 공유할 때 "
            f"신뢰를 얻습니다. '기대 vs 현실' 프레임은 B2B 구매 지연을 줄이는 "
            f"콘텐츠 장르로도 적합합니다. "
            f"Workspace Agents는 이메일·문서·캘린더 맥락을 묶는다는 점에서 "
            f"잠재력이 크지만, 복잡한 다단계 캠페인 기획에는 아직 "
            f"수동 검수가 필요합니다. 팀별로 '에이전트에게 맡길 수 있는 것' "
            f"과 '사람이 반드시 확인할 것' 목록을 분리해 문서화하면 "
            f"내부 설득과 외부 콘텐츠화를 동시에 할 수 있습니다. "
            f"OpenAI 공식 발표와 Reddit 현장 의견의 간극 자체가 "
            f"좋은 교육 소재가 됩니다."
        )

    if key == "ai_ide":
        return (
            f"{index}번째 주제는 {title}입니다. "
            f"AI IDE(Cursor·Windsurf)는 Agent 모드와 Background Agent로 "
            f"코딩·콘텐츠 제작 워크플로를 재편하고 있습니다. "
            f"{ctx} "
            f"마케터·콘텐츠 팀에게는 '개발자 전용 도구'가 아니라 "
            f"바이브 코딩으로 랜딩·자동화 스크립트·내부 도구를 "
            f"빠르게 만드는 생산성 레이어로 인식해야 합니다. "
            f"다만 무료 트rial 우회 같은 그레이존 튜토리얼은 "
            f"브랜드 콘텐츠에서 거리를 두고, 정식 라이선스·팀 플랜·"
            f"보안 정책 관점의 비교 글이 B2B 신뢰에 유리합니다. "
            f"Cursor vs Windsurf 선택 가이드는 기능 나열보다 "
            f"'우리 팀이 매주 반복하는 작업'에 어떤 Agent 모드가 "
            f"맞는지 실습 영상·FAQ로 풀면 검색·교육 수요를 동시에 "
            f"잡을 수 있습니다. AX 전환 로드맵에서는 개발 조직뿐 아니라 "
            f"마케팅·운영의 바이브 코딩 역량을 함께 올리는 "
            f"교육 모듈로 포함하는 것이 좋습니다."
        )

    if key == "aeo":
        return (
            f"{index}번째 주제는 {title}입니다. "
            f"CXL 등 AEO 가이드는 Answer Engine이 권위 있고 최신 콘텐츠를 "
            f"선호한다고 정리합니다. "
            f"기존 SEO의 크롤링·인덱싱·메타데이터 원칙은 유지하면서, "
            f"FAQ 구조화·Direct Answer 문단·출처·갱신일 표기를 추가하는 것이 "
            f"2026년 검색 전략의 실무 핵심입니다. "
            f"{ctx} "
            f"한국 B2B 블로그는 '키워드 나열'에서 '질문 하나에 답 하나' 형식으로 "
            f"바꿀수록 ChatGPT·Perplexity·Gemini 인용 가능성이 높아집니다. "
            f"Search Engine Journal·SEO.com 등 2026년 분석처럼 "
            f"FAQ schema 적용 시 AI 인용률 개선 사례가 보고되므로, "
            f"블로그 HTML JSON-LD와 packages 평문 FAQ를 동기화해야 합니다. "
            f"신선도 신호는 '업데이트: YYYY-MM-DD'를 본문·메타·"
            f"GEO 인용 블록에 동일하게 넣는 것만으로도 충분한 경우가 많습니다. "
            f"AEO는 SEO를 대체하지 않고, AI 답변 레이어를 "
            f"추가하는 전략으로 이해하는 것이 혼선을 줄입니다."
        )

    return (
        f"{index}번째 인사이트 {title}에 대해 정리합니다. "
        f"{ctx} "
        f"글로벌 신호를 국내 AX·에이전트 도입 맥락에 맞게 재해석하면 "
        f"FAQ형 블로그, 소셜 캐러셀, LinkedIn 인사이트 포스트로 "
        f"일관된 메시지를 유지할 수 있습니다."
    )


def build_practical_application(insights: list[Insight], summary: str) -> list[str]:
    """출처 분석 기반 실무 적용 항목 (generic 체크리스트 대신)."""
    steps: list[str] = []
    for ins in insights[:7]:
        key = _insight_topic_key(ins)
        if key == "ax":
            steps.append(
                "AX 전환: 임원·현장 교육 세션으로 'PoC 이전 조직 정렬'을 먼저 진행합니다. "
                "출처가 강조한 '운영 전반 AI 통합'을 직군별 FAQ 5개로 쪼개 "
                "Direct Answer 블록과 JSON-LD FAQPage에 반영합니다."
            )
            steps.append(
                "AX 리드 생성: 컨설팅·강의 랜딩에 '한국 AX 여정' 사례 페이지를 분리하고, "
                "블로그 본문과 내부 링크로 연결합니다. "
                "교육·FAQ·사례 3종 세트가 PoC 단독보다 전환율이 높습니다."
            )
        elif key == "agent_marketing":
            steps.append(
                "에이전트 도입: 마케팅 반복 업무(주간 리포트, CRM 업데이트, 캠페인 초안) "
                "3개를 팀별로 목록화한 뒤, Reddit 실무 비교에서 언급된 use case 기준으로 "
                "빌더를 고릅니다. hype가 아닌 '우리 업무 → 자동화 단계' 매핑표를 만듭니다."
            )
            steps.append(
                "에이전트 운영: 프롬프트·SOP·KPI 3종을 표준화한 다음 2주 파일럿을 돌립니다. "
                "2026 agency 경험담처럼 '무엇을 바꿀지'를 문서화하면 "
                "LinkedIn·내부 교육 소재로 바로 재사용할 수 있습니다."
            )
        elif key == "workspace_agents":
            steps.append(
                "Workspace Agents: Pro 플랜 한계와 팀 협업 시나리오 2~3개를 정해 "
                "기대 vs 실제 출력을 기록합니다. "
                "현장 피드백('생각보다 덜 똑똑')을 숨기지 않고 교육 콘텐츠로 공개하면 "
                "B2B 신뢰도가 올라갑니다."
            )
        elif key == "aeo":
            steps.append(
                "AEO: FAQ 3개 이상을 schema.org FAQPage JSON-LD로 구조화하고, "
                "각 답변에 출처 URL·갱신일을 명시합니다. "
                "Answer Engine은 정확성·신선도 신호를 함께 봅니다."
            )
        elif key == "ai_ide":
            steps.append(
                "AI IDE: Cursor·Windsurf를 팀 표준 도구로 비교할 때 "
                "무료 트rial 우회가 아닌 라이선스·보안·Agent 모드 실습 기준으로 "
                "평가합니다. 마케팅 팀용 '바이브 코딩 101' FAQ를 "
                "강의·블로그와 연결합니다."
            )

    if not steps:
        steps = [
            "주간 리서치 5건을 하나의 통합 컨텍스트로 묶은 뒤 채널별로 재가공합니다.",
            "Direct Answer 문단을 LinkedIn 훅·Instagram 1슬라이드로 분리합니다.",
        ]

    steps.append(
        "통합 운영: brief → 본 아티클 → 강의 아웃라인 순 내부 링크를 연결하고, "
        "모든 주장에 1차 출처와 2차 검증 메모(시의성·신뢰도)를 남깁니다."
    )
    return steps[:8]


def build_faq_answer(ins: Insight) -> str:
    """FAQ 답변 — AEO Direct Answer용 완결 문장 2~4개."""
    parts: list[str] = []
    for field in (ins.insight_derivation, ins.summary, ins.marketer_view, ins.korea_apply):
        val = (field or "").strip()
        if not val or not has_meaningful_korean(val):
            continue
        if any(val in p or p in val for p in parts):
            continue
        parts.append(val)
        if len(parts) >= 2:
            break
    text = " ".join(parts) if parts else ins.korean_summary
    return compress_sentences(text, 420, max_sentences=4)


def build_faq_items(insights: list[Insight], summary: str) -> list[tuple[str, str]]:
    if not insights:
        return [
            (
                "AEO란 무엇이며 SEO와 어떻게 다른가요?",
                compress_sentences(summary, 360, max_sentences=3),
            ),
            (
                "2026년 AI 마케팅에서 에이전트 자동화를 어떻게 시작하나요?",
                compress_sentences(summary, 360, max_sentences=3),
            ),
            (
                "한국 B2B 시장에서 AX 전환 콘텐츠 기회는?",
                compress_sentences(summary, 360, max_sentences=3),
            ),
        ]
    faqs: list[tuple[str, str]] = []
    q_templates = [
        "{}이란 무엇이며 B2B 마케터에게 왜 중요합니까?",
        "{} — 실무에서는 어디부터 시작하면 좋습니까?",
        "{}가 팀 운영과 콘텐츠 전략에 주는 변화는 무엇입니까?",
    ]
    for i, ins in enumerate(insights[:3]):
        title = ins.korean_title
        q = q_templates[i].format(title) if i < len(q_templates) else title
        faqs.append((q, build_faq_answer(ins)))
    return faqs


def build_blog_html(stamp: str, summary: str, insights: list[Insight]) -> str:
    primary = insights[0] if insights else None
    topic = primary.korean_title if primary else "AI 마케팅 트렌드"
    slug = slugify(topic)
    title = truncate(f"{topic} — 실무 가이드", 58)
    meta = truncate(summary, 155)
    faqs = build_faq_items(insights, summary)
    direct = truncate(summary, 320)

    sections_html = (
        f"<section><h2>왜 지금 이 주제인가?</h2>"
        f"<p>2026년 B2B 마케팅은 AI 검색(AEO)과 에이전트 자동화가 "
        f"동시에 요구돼요. {html.escape(humanize(direct, genre='blog').text)}</p></section>\n"
    )
    if insights:
        items = "".join(
            f"<li><strong>{html.escape(ins.korean_title)}</strong> — "
            f"{html.escape(ins.context_blurb(max_chars=160, max_sentences=2))}</li>"
            for ins in insights[:3]
        )
        sections_html += f"<section><h2>핵심 트렌드 3가지</h2><ul>{items}</ul></section>\n"
    sections_html += (
        "<section><h2>실무 적용 체크리스트</h2><ol>"
        "<li>주간 리서치 브리프로 트렌드 5건 모으기</li>"
        "<li>FAQ 3개 이상 구조화 + JSON-LD 적용</li>"
        "<li>블로그 → 인스타 캐러셀 → 링크드인 재가공</li>"
        "<li>출처 URL·날짜 명시 (GEO 신선도)</li>"
        "</ol></section>\n"
    )

    faq_html = ""
    for q, a in faqs:
        faq_html += f"""
      <div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
        <h3 itemprop="name">{html.escape(q)}</h3>
        <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
          <p itemprop="text">{html.escape(a)}</p>
        </div>
      </div>"""

    sources_html = ""
    for ins in insights[:3]:
        if ins.url:
            sources_html += f'<li><a href="{html.escape(ins.url)}">{html.escape(ins.korean_title)}</a></li>'

    faq_jsonld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs
        ],
    }
    article_jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "datePublished": stamp,
        "author": {"@type": "Organization", "name": "Hermes Content Studio"},
        "description": meta,
    }

    template = read_template("templates/html/blog-post.html")
    replacements = {
        "{{TITLE}}": title,
        "{{META_DESCRIPTION}}": meta,
        "{{CANONICAL_URL}}": f"https://content-studio.local/blog/{stamp}_{slug}",
        "{{DATE_ISO}}": stamp,
        "{{DATE_DISPLAY}}": stamp,
        "{{READ_TIME}}": "7",
        "{{DIRECT_ANSWER}}": direct,
        "{{SECTIONS}}": sections_html,
        "{{FAQ_ITEMS}}": faq_html,
        "{{SOURCES_LIST}}": sources_html or "<li>주간 리서치 브리프 참조</li>",
        "{{TAGS}}": "AI, AEO, GEO, Agentic AI, Marketing, AX",
        "{{FAQ_JSONLD}}": json.dumps(faq_jsonld, ensure_ascii=False, indent=2),
        "{{ARTICLE_JSONLD}}": json.dumps(article_jsonld, ensure_ascii=False, indent=2),
        "{{GEO_QUOTE}}": compress_sentences(
            insights[0].context_blurb(max_chars=200, max_sentences=2)
            if insights
            else summary,
            200,
            max_sentences=2,
        ),
    }
    result = template
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result


def build_gemini_instagram_feed_prompt(
    slide_num: int,
    kind: str,
    headline: str,
    body_lines: list[str],
    topic: str,
) -> str:
    """Instagram 뉴스피드 캐러셀 · 4:5 · Nano Banana Pro 2 · 정보형 카드 · 나눔고딕."""
    layout = {
        "Hook": (
            "top 35% bold headline zone, minimal eye-catching icon or abstract AI motif, "
            "soft warm gradient background (#FAFAFA to #FFF8E7), swipe cue hint at right edge"
        ),
        "Insight": (
            "headline bar + 2-3 bullet cards with simple icons, clean infographic layout, "
            "generous whitespace, educational save-worthy information design"
        ),
        "CTA": (
            "centered bookmark/save motif, bold CTA headline, bottom yellow accent bar (#FFE500, 8% height), "
            "warm closing composition encouraging save and share"
        ),
    }.get(kind, "clean informational card layout with clear hierarchy")

    korean_text_rules = (
        "CRITICAL: All Korean Hangul text must be perfectly legible with no broken, "
        "corrupted, or gibberish characters. Use Nanum Gothic Bold (나눔고딕 Bold) for "
        "headlines and Nanum Gothic Regular (나눔고딕) for body lines. Max 3 short lines "
        "per slide. Render exact Korean strings provided — do not translate or paraphrase."
    )
    style = (
        "Professional Korean informational Instagram feed carousel slide, "
        "1080x1350 pixels, 4:5 vertical portrait aspect ratio, 2026 Instagram feed "
        "optimized educational infographic card, clean flat design, high contrast "
        "readable typography, soft brand accent #FFE500 sparingly, "
        "safe zone: keep all text and icons within center 80% width and middle "
        "1080x1080 region for profile grid crop compatibility"
    )
    body_spec = "; ".join(
        f"body line {i + 1} exactly 「{line}」" for i, line in enumerate(body_lines[:3])
    )
    negative = (
        "Avoid: broken Korean text, wrong Hangul, English-only text, blurry letters, "
        "watermark, logo clutter, photorealistic photo, 3D render, western comic style, "
        "speech bubbles, tiny unreadable font, gradient overload, square 1:1 crop, "
        "landscape layout, cluttered layout, meme style"
    )
    api_block = (
        "Gemini API: model=gemini-3-pro-image-preview (Nano Banana Pro 2), "
        "aspect_ratio=4:5, image_size=2K, response_modalities=['TEXT','IMAGE']"
    )
    alt = f"{kind} — {headline[:30]} · {' / '.join(body_lines[:2])[:40]}"
    return (
        f"[Instagram Feed Carousel {slide_num}/3 — {kind} · 4:5 Portrait · 1080×1350]\n"
        f"Prompt: {style}. Layout: {layout}. Topic context: {truncate(topic, 60)}. "
        f"Headline text exactly 「{headline}」. {body_spec}. {korean_text_rules}\n"
        f"Negative: {negative}\n"
        f"Alt text (KO): {alt}\n"
        f"{api_block}"
    )


def build_gemini_webtoon_prompt(
    slide_num: int,
    kind: str,
    dialogue_female: str,
    dialogue_male: str,
    scene_note: str = "",
) -> str:
    """Gemini Nano Banana Pro용 웹툰 캐러셀 이미지 프롬프트 (한국어·Pretendard)."""
    scene = scene_note or (
        "cozy Korean-style cafe interior, soft daylight, warm and approachable atmosphere"
    )
    korean_text_rules = (
        "CRITICAL: All Korean Hangul text must be perfectly legible with no broken, "
        "corrupted, or gibberish characters. Use Pretendard sans-serif font for every "
        "speech bubble. Short lines only (max 2 lines per bubble)."
    )
    style = (
        "Korean webtoon / manhwa illustration style, clean line art, soft cel-shading, "
        "modern Korean digital comic aesthetic, 1080x1080 square Instagram carousel frame, "
        "generous white margins around speech bubbles, white rounded speech bubbles with "
        "clear padding, natural conversational poses"
    )
    characters = (
        "Two Korean characters: a friendly young professional woman (shoulder-length hair, "
        "smart casual) and a young professional man (neat short hair, casual blazer), "
        "talking naturally face-to-face or side-by-side, expressive but not exaggerated"
    )
    bubble_layout = (
        f"Slide {slide_num} ({kind}): woman's speech bubble text exactly: "
        f"「{dialogue_female}」; man's speech bubble text exactly: 「{dialogue_male}」. "
        "Place bubbles with white space between them, never overlapping faces."
    )
    negative = (
        "Avoid: broken Korean text, wrong Hangul, English-only text, blurry letters, "
        "watermark, logo, photorealistic, 3D render, western comic style, emoji, "
        " cluttered layout, tiny unreadable font, gradient overload"
    )
    api_block = (
        "Gemini API: model=gemini-3-pro-image-preview (Nano Banana Pro), "
        "aspect_ratio=1:1, image_size=2K, response_modalities=['TEXT','IMAGE']"
    )
    return (
        f"[Carousel {slide_num}/3 — {kind}]\n"
        f"Prompt: {style}. {characters}. Scene: {scene}. {bubble_layout} "
        f"{korean_text_rules}\n"
        f"Negative: {negative}\n"
        f"Alt text (KO): 여성 「{dialogue_female[:40]}」, 남성 「{dialogue_male[:40]}」 — {kind}\n"
        f"{api_block}"
    )


def build_gemini_linkedin_2x2_prompt(
    panels: list[tuple[str, str, str]],
    topic: str,
) -> str:
    """LinkedIn 1:1 단일 이미지 · 2×2 웹툰 패널 · Gemini Nano Banana Pro 2."""
    style = (
        "Korean webtoon / manhwa illustration style, clean line art, soft cel-shading, "
        "modern Korean digital comic aesthetic, single 1080x1080 square LinkedIn feed image, "
        "2x2 comic panel grid layout with clear gutters between panels, "
        "each panel shows two Korean characters (friendly young professional woman with "
        "shoulder-length hair and young professional man with neat short hair) "
        "in natural conversational poses, white rounded speech bubbles with generous padding"
    )
    korean_text_rules = (
        "CRITICAL: All Korean Hangul text must be perfectly legible with no broken, "
        "corrupted, or gibberish characters. Use Pretendard sans-serif font for every "
        "speech bubble. Max 2 lines per bubble. Never overlap faces with text."
    )
    panel_specs: list[str] = []
    positions = ["top-left", "top-right", "bottom-left", "bottom-right"]
    for (label, female, male), pos in zip(panels, positions):
        panel_specs.append(
            f"Panel {label} ({pos}): woman's bubble exactly 「{female}」; "
            f"man's bubble exactly 「{male}」"
        )
    negative = (
        "Avoid: broken Korean text, wrong Hangul, English-only text, blurry letters, "
        "watermark, logo, photorealistic, 3D render, western comic style, emoji, "
        "single panel only, vertical strip layout, cluttered layout, tiny unreadable font"
    )
    api_block = (
        "Gemini API: model=gemini-3-pro-image-preview (Nano Banana Pro 2), "
        "aspect_ratio=1:1, image_size=2K, response_modalities=['TEXT','IMAGE']"
    )
    alt_parts = " · ".join(f"{lbl}: {f[:20]}" for lbl, f, _ in panels)
    return (
        f"[LinkedIn 1:1 · 2×2 Webtoon — {truncate(topic, 40)}]\n"
        f"Prompt: {style}. Topic context: {truncate(topic, 60)}. "
        f"{' '.join(panel_specs)}. {korean_text_rules}\n"
        f"Negative: {negative}\n"
        f"Alt text (KO): 2×2 대화형 웹툰 — {alt_parts}\n"
        f"{api_block}"
    )


def build_image_prompt(
    slide_num: int,
    kind: str,
    headline: str,
    body: str,
    colors: list[str] | None = None,
) -> str:
    """Legacy alias — 웹툰 캐러셀용 Gemini 프롬프트로 위임."""
    return build_gemini_webtoon_prompt(
        slide_num,
        kind,
        dialogue_female=headline,
        dialogue_male=body[:80],
    )


def build_instagram_hashtags(ins: Insight | None) -> str:
    """Instagram feed — 해시태그 5개 (과다 태그 스팸 신호 회피)."""
    key = _insight_topic_key(ins) if ins else "general"
    pools: dict[str, list[str]] = {
        "llm_anthropic": ["#ClaudeAI", "#LLM", "#AIMarketing", "#B2B마케팅", "#AX"],
        "llm_google": ["#GeminiAI", "#GoogleAI", "#AEO", "#마케팅트렌드", "#디지털마케팅"],
        "llm_perplexity": ["#Perplexity", "#GEO", "#AEO", "#AIMarketing", "#마케팅트렌드"],
        "korea_ax": ["#AX", "#AI전환", "#B2B마케팅", "#마케팅트렌드", "#디지털마케팅"],
        "korea_adoption": ["#AI도입", "#AX", "#B2B마케팅", "#마케팅트렌드", "#디지털마케팅"],
        "agent_marketing": ["#AI에이전트", "#마케팅자동화", "#AIMarketing", "#B2B마케팅", "#AgenticAI"],
        "harness_engineering": ["#HarnessEngineering", "#프롬프트엔지니어링", "#AIMarketing", "#마케팅트렌드", "#디지털마케팅"],
        "hermes_agent": ["#HermesAgent", "#AI에이전트", "#오픈소스", "#AIMarketing", "#AX"],
        "aeo": ["#AEO", "#GEO", "#SEO", "#AIMarketing", "#마케팅트렌드"],
        "ai_governance": ["#AI거버넌스", "#ResponsibleAI", "#AIMarketing", "#B2B마케팅", "#AX"],
        "ai_literacy": ["#AI리터러시", "#마케팅교육", "#AIMarketing", "#B2B마케팅", "#디지털마케팅"],
    }
    default = ["#AIMarketing", "#AEO", "#디지털마케팅", "#마케팅트렌드", "#B2B마케팅"]
    return " ".join(pools.get(key, default)[:5])


def instagram_carousel_spec(
    summary: str, insights: list[Insight]
) -> tuple[str, list[tuple[str, str, list[str]]]]:
    """3장 캐러셀 Hook/Insight/CTA 스펙 — channel md · Notion context 공용."""
    topic = insights[0].korean_title if insights else "AI 마케팅"
    hook = truncate(topic, 22)
    ins1 = insights[0] if insights else None
    ins2 = insights[1] if len(insights) > 1 else None
    insight_title = truncate(ins1.korean_title, 28) if ins1 else "AEO·에이전트 트렌드"
    insight_line1 = (
        truncate(ins1.insight_derivation or ins1.korean_summary, 42)
        if ins1
        else truncate(summary, 42)
    )
    insight_line2 = (
        truncate(ins2.korean_title, 36) if ins2 else "실무 FAQ·Direct Answer가 핵심"
    )
    if re.search(r"[A-Za-z]{5,}", insight_line2):
        insight_line2 = "저장해두면 팀 미팅에 바로 써요"
    carousel_spec: list[tuple[str, str, list[str]]] = [
        (
            "Hook",
            f"2026 {hook}",
            ["B2B 마케팅, 뭐가 바뀌었을까?", "→ 스와이프 · 저장 추천 ↓"],
        ),
        ("Insight", insight_title, [insight_line1, insight_line2]),
        ("CTA", "실무에 바로 써요", ["캐러셀 저장 📌", "팀과 공유하기"]),
    ]
    return topic, carousel_spec


def append_instagram_gemini_prompts(
    lines: list[str],
    carousel_spec: list[tuple[str, str, list[str]]],
    topic: str,
    *,
    heading: str = "## Gemini 이미지 생성 프롬프트 (3장)",
) -> None:
    """슬라이드별 Nano Banana Pro 2 프롬프트 — Notion·channel 공용."""
    lines.extend([heading, ""])
    for i, (kind, headline, body_lines) in enumerate(carousel_spec, 1):
        lines.extend(
            [
                f"### Slide {i}/3 — {kind}",
                f"- **헤드라인:** {headline}",
                f"- **본문:** {' · '.join(body_lines)}",
                "",
                "```",
                build_gemini_instagram_feed_prompt(i, kind, headline, body_lines, topic),
                "```",
                "",
            ]
        )


def linkedin_webtoon_panels(insights: list[Insight]) -> list[tuple[str, str, str]]:
    ins0 = insights[0] if insights else None
    ins1 = insights[1] if len(insights) > 1 else None
    topic = ins0.korean_title if ins0 else "2026 AI 마케팅"
    return [
        ("1 Hook", "요즘 AX, 뭐부터 해요?", truncate(topic, 22)),
        ("2 Problem", "빌더부터 고르면 망해요", "반복 업무부터요!"),
        (
            "3 Insight",
            truncate(ins0.korean_title, 18) if ins0 else "AX는 FAQ부터",
            truncate(ins0.korean_summary, 28) if ins0 else "교육·사례로 끌어당기기",
        ),
        ("4 CTA", "실습 하나만!", "반복 업무 3개 적어보세요"),
    ]


def build_linkedin_post_text(summary: str, insights: list[Insight]) -> str:
    """LinkedIn 포스트 본문만 (이미지 프롬프트 제외)."""
    topic = insights[0].korean_title if insights else "2026 AI 마케팅"
    hook1 = (
        f"한국 B2B, {truncate(topic, 35)} — "
        f"‘언제’보다 ‘어디서’ 손대느냐가 더 중요해요."
        if insights
        else "2026 AI 마케팅, 뭐가 바뀌었는지부터 짚어볼게요."
    )
    hook2 = "에이전트 도구 고르기 전에 프롬프트·SOP·측정 3가지만 잡아도 속도가 달라져요."
    bullets: list[str] = []
    ins0 = insights[0] if insights else None
    ins1 = insights[1] if len(insights) > 1 else None
    ins2 = insights[2] if len(insights) > 2 else None
    fallbacks = [
        ("AX는 PoC보다 교육·FAQ·사례로 끌어당기는 단계예요", (ins0.korean_summary[:60] if ins0 else "")),
        ("에이전트는 반복 업무 3개부터 시작해요", (ins1.korean_summary[:60] if ins1 else "프롬프트·체크리스트·KPI 먼저")),
        ("한국 시장은 실행 직전 가이드 수요가 커요", (ins2.korean_summary[:60] if ins2 else "선언형 AI보다 실무 프레임")),
    ]
    for title_line, detail in fallbacks[:3]:
        bullets.append(f"→ {title_line}")
        if detail:
            bullets.append(f"  {detail}")
    post_parts = [
        hook1,
        hook2,
        "",
        "2026년 상반기엔 AX·AI 에이전트 이야기가 동시에 올라와요.",
        "현장에서 자주 보이는 실패는 ‘에이전트 빌더부터 고르기’예요.",
        "",
        "저는 주간 리서치 돌려보니 패턴이 이렇게 보여요.",
        "",
        *bullets,
        "",
        "이번 주 실습: 팀 반복 업무 3개만 적어 보세요.",
        "그다음에 에이전트·자동화 얘기가 훨씬 수월해져요.",
        "",
        "팀에서 AX/에이전트, 어디부터 시작하고 계세요?",
        "",
        "#AIMarketing #AEO #AgenticAI #B2BMarketing #AX",
    ]
    post = humanize_linkedin_post("\n".join(post_parts)).text.strip()
    while len(post) > 1300:
        post = post[:1297] + "..."
    return post


def build_linkedin_image_prompt(insights: list[Insight]) -> str:
    topic = insights[0].korean_title if insights else "2026 AI 마케팅"
    panels = linkedin_webtoon_panels(insights)
    return build_gemini_linkedin_2x2_prompt(panels, topic)


def build_instagram_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    topic, carousel_spec = instagram_carousel_spec(summary, insights)
    ins1 = insights[0] if insights else None
    hook = truncate(topic, 22)
    insight_title = carousel_spec[1][1]
    hashtags = build_instagram_hashtags(ins1)
    caption_hook = f"💬 {hook} — 2026 B2B 마케팅, AEO와 에이전트가 동시에 요구돼요."

    lines = [
        f"# 인스타그램 캐러셀 — {topic}",
        f"**날짜:** {stamp}",
        f"**형식:** 3장 캐러셀 · 1080×1350 (4:5 세로) · 뉴스피드 정보형",
        f"**이미지 엔진:** Gemini Nano Banana Pro 2 (`gemini-3-pro-image-preview`)",
        f"**타이포:** 나눔고딕 (Nanum Gothic) · Hangul 깨짐 방지",
        "",
        "## 뉴스피드 알고리즘 최적화",
        "- **비율:** 4:5 (1080×1350) — 2026 피드 세로 점유·정보형 캐러셀 권장",
        "- **1장 훅:** 3초 내 스크롤 정지 · 저장 암시 (swipe cue)",
        "- **2장 가치:** 저장형 인사이트 · 불릿 2~3개 · 완독 유도",
        "- **3장 CTA:** 저장·공유 명시 — 미완독 시 알고리즘 재노출 신호",
        "- **캡션:** 첫 125자 훅 · 줄바꿈 가독성 · 해시태그 5개",
        "- **안전 영역:** 텍스트·아이콘 중앙 1080×1080 (프로필 그리드 크롭 대비)",
        "",
        "## 제작 조건",
        "- [x] 한국어 전용 (Hangul 정확 렌더링 — 프롬프트에 문구 명시)",
        "- [x] 나눔고딕 Bold/Regular",
        "- [x] 캐러셀 3장 (Hook → Insight → CTA)",
        "- [x] 슬라이드별 alt text",
        "- [x] Gemini: aspect_ratio=4:5, image_size=2K",
        "- [x] 해시태그 5개",
        "",
    ]

    append_instagram_gemini_prompts(lines, carousel_spec, topic)

    takeaway = ins1.korean_summary[:140] if ins1 else summary[:140]

    lines.extend(
        [
            "## 캡션 (가독성 최적화)",
            "",
            caption_hook,
            "",
            "2026년 B2B 마케팅, AI 검색(AEO)과 에이전트 자동화가 동시에 요구되고 있어요.",
            "",
            f"📌 이번 핵심",
            f"→ {insight_title}" if ins1 else f"→ {truncate(summary, 50)}",
            "",
            "💡 한 줄 정리",
            takeaway,
            "",
            "👉 캐러셀 저장해두고 팀과 공유해 보세요.",
            "프로필 링크에서 전체 가이드를 확인할 수 있어요.",
            "",
            "---",
            "",
            "## 해시태그 (5개)",
            hashtags,
            "",
            "## 출처",
        ]
    )
    for ins in insights[:3]:
        if ins.url:
            lines.append(f"- {ins.korean_title}: {ins.url}")
    return "\n".join(lines)


def build_linkedin_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """LinkedIn: casual 해요체 포스트 + 1:1 2×2 웹툰 Gemini 프롬프트."""
    post = build_linkedin_post_text(summary, insights)
    image_prompt = build_linkedin_image_prompt(insights)
    return "\n".join(
        [
            post,
            "",
            "---",
            "이미지 생성 프롬프트 (Gemini Nano Banana Pro 2 · 1:1 · 2×2 웹툰)",
            "",
            "```",
            image_prompt,
            "```",
        ]
    )


def _char_count(text: str) -> int:
    return len(text)


def _trim_to_chars(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def build_blog_article_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """블로그: LinkedIn형 평문 · ~합니다/~입니다 · 출처 기반 확장 본문."""
    primary = insights[0] if insights else None
    topic = primary.korean_title if primary else "AI 마케팅 트렌드"
    faqs = build_faq_items(insights, summary)
    practical = build_practical_application(insights, summary)

    direct = humanize(truncate(summary, 320), genre="blog").text

    intro = (
        "2026년 B2B 마케팅 현장에서는 AI 검색(AEO)과 에이전트 자동화가 "
        "동시에 요구됩니다. 이번 주 리서치를 바탕으로 "
        f"{topic} 관점에서 무엇이 바뀌었는지, 현장에 어떻게 적용할 수 있는지 "
        "정리했습니다. 아래 내용은 Top 7 인사이트와 심층 분석을 "
        "하나의 아티클로 통합한 것입니다."
    )
    intro2 = (
        "에이전트 자동화, AEO, AX 전환은 더 이상 별개의 주제가 아닙니다. "
        "검색에서 답을 찾는 방식이 바뀌면서 FAQ와 Direct Answer가 필수가 되었고, "
        "동시에 마케팅·운영 팀은 반복 업무를 에이전트로 넘기는 실험을 "
        "본격화하고 있습니다. 한국 시장에서는 '선언형 AI'보다 "
        "'실행 직전 가이드'와 교육·컨설팅 콘텐츠 수요가 더 크게 나타납니다."
    )

    body_parts: list[str] = [
        f"## {topic}",
        "",
        "## 한 줄 요약",
        direct,
        "",
        intro,
        "",
        intro2,
        "",
    ]

    if insights:
        titles = " · ".join(truncate(ins.korean_title, 40) for ins in insights[:3])
        body_parts.append(f"이번 주 핵심 축은 {titles} 세 가지로 읽힙니다.")
        body_parts.append("")
        for i, ins in enumerate(insights[:7], 1):
            body_parts.append(f"### {ins.korean_title}")
            body_parts.append("")
            body_parts.append(humanize(expand_insight_body(ins, i), genre="blog").text)
            body_parts.append("")
            body_parts.append(
                humanize(
                    f"위 주제를 콘텐츠로 풀 때는 '{ins.korean_title}' 키워드로 "
                    f"Direct Answer 한 문단, FAQ 2개, LinkedIn 불릿 1개를 "
                    f"동일 메시지로 맞추는 것이 좋습니다. "
                    f"{truncate(ins.opportunity or ins.korea_apply or ins.marketer_view, 120)}",
                    genre="blog",
                ).text
            )
            body_parts.append("")

    cross = (
        "세 축을 교차해 보면 공통 패턴이 보입니다. AX는 조직 전체의 AI 통합 "
        "이야기이고, 에이전트는 팀 단위 자동화 실행 레이어이며, "
        "AEO는 그 지식이 검색·AI 답변 엔진에 인용되도록 만드는 "
        "배포 레이어입니다. 리서치를 한 번만 깊게 하고 "
        "블로그(Direct Answer) → LinkedIn(훅·불릿) → Instagram(웹툰 캐러셀) "
        "순으로 재가공하면 제작 시간 대비 도달 범위를 극대화할 수 있습니다. "
        "특히 한국 B2B는 구매 전에 '우리 팀에 맞는지'를 FAQ와 사례로 "
        "확인하려는 경향이 강하므로, PoC 성과만 강조하기보다 "
        "교육·체크리스트·실습 과제를 함께 제공하는 편이 전환에 유리합니다. "
        "브리프의 심층 분석처럼 에이전트 자동화 × AEO × AX 전환은 "
        "2026년 B2B 마케팅의 공통 축입니다. 검색과 소셜을 분리하지 않고 "
        "통합 컨텍스트로 한 번 리서치한 뒤 채널별 톤만 조정하는 것이 "
        "효율적입니다. Primary 키워드(AI marketing, Agentic AI, AEO)와 "
        "Long-tail(2026 B2B 콘텐츠 자동화, AI 검색 최적화)을 "
        "FAQ 질문 문장에 자연스럽게 녹이면 SEO와 AEO를 동시에 "
        "충족할 수 있습니다. GEO 관점에서는 출처 URL, 갱신일, "
        "인용 가능한 요약 블록을 HTML·평문 아티클 모두에 "
        "동일하게 유지해야 합니다."
    )
    body_parts.extend([cross, "", "## 실무 적용", ""])
    for n, step in enumerate(practical, 1):
        body_parts.append(f"{n}. {humanize(step, genre='blog').text}")
    body_parts.append("")

    body_parts.append("## FAQ")
    body_parts.append("")
    for q, a in faqs:
        body_parts.extend(
            [
                f"Q. {q}",
                f"A. {humanize(a, genre='blog').text}",
                "",
            ]
        )

    geo_quote = humanize(
        compress_sentences(
            insights[0].context_blurb(max_chars=240, max_sentences=2)
            if insights
            else summary,
            240,
            max_sentences=2,
        ),
        genre="blog",
    ).text
    body_parts.extend(
        [
            "## GEO 인용",
            geo_quote,
            "",
            "## 출처",
        ]
    )
    for ins in insights[:3]:
        if ins.url:
            body_parts.append(f"- {ins.korean_title}: {ins.url}")
    body_parts.extend(
        [
            "",
            f"Title tag: {truncate(topic + ' — 실무 가이드', 58)}",
            f"Meta description: {truncate(summary, 155)}",
            "Keywords: AEO, GEO, Agentic AI, AX, B2B Marketing",
            "",
        ]
    )

    article = "\n".join(body_parts)
    return _trim_to_chars(article, 15000)


def build_instagram_context_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Notion용 인스타그램 최적화 컨텍스트 (3장 정보형 캐러셀 · 4:5 · Gemini 프롬프트 전문)."""
    topic, carousel_spec = instagram_carousel_spec(summary, insights)
    ins1 = insights[0] if insights else None
    hook = truncate(topic, 22)
    insight_title = carousel_spec[1][1]
    insight_line1 = carousel_spec[1][2][0]
    hashtags = build_instagram_hashtags(ins1)

    lines = [
        f"# Instagram 컨텍스트 — {topic}",
        f"**날짜:** {stamp} · **용도:** 3장 정보형 캐러셀 + 캡션",
        "",
        "## 뉴스피드 알고리즘",
        "- **저장·완독:** 정보형 캐러셀 → save rate · swipe completion ↑",
        "- **재노출:** 미완독 캐러셀은 피드에서 재노출 (완독 유도 설계)",
        "- **1장 훅:** 3초 내 스크롤 정지 · 저장 암시",
        "- **캡션 훅:** 첫 125자에 핵심 가치",
        "",
        "## 플랫폼·이미지 스펙",
        "- **엔진:** Gemini Nano Banana Pro 2 (`gemini-3-pro-image-preview`)",
        "- **장수:** 3장 (Hook → Insight → CTA)",
        "- **비율:** 4:5 · 1080×1350 · 2K (2026 피드 권장)",
        "- **폰트:** 나눔고딕 (Nanum Gothic) · Hangul 정확 렌더링",
        "- **포맷:** 정보형 인포그래픽 카드 (저장형 교육 콘텐츠)",
        "- **안전 영역:** 중앙 1080×1080 (그리드 크롭 대비)",
        "",
        "## 캐러셀 구조 (3장)",
        "| # | 역할 | 헤드라인 | 본문 |",
        "|---|------|----------|------|",
        f"| 1 | Hook | 2026 {hook} | B2B 마케팅 변화 · 스와이프 유도 |",
        f"| 2 | Insight | {insight_title} | {insight_line1} |",
        "| 3 | CTA | 실무에 바로 써요 | 저장 · 팀 공유 |",
        "",
    ]

    append_instagram_gemini_prompts(lines, carousel_spec, topic)

    lines.extend(
        [
            "## 캡션 (가독성)",
            "",
            f"💬 {hook} — 2026 B2B 마케팅, AEO와 에이전트가 동시에 요구돼요.",
            "",
            truncate(summary, 180),
            "",
            f"📌 핵심 → {insight_title}",
            "",
            "👉 캐러셀 저장 + 프로필 링크",
            "",
            "## 해시태그 (5개)",
            hashtags,
            "",
            "## 출처",
            *_insight_source_lines(insights, limit=3),
        ]
    )
    return "\n".join(lines)


def _insight_source_lines(insights: list[Insight], limit: int = 5) -> list[str]:
    lines: list[str] = []
    for ins in insights[:limit]:
        if ins.url:
            lines.append(f"- {truncate(ins.korean_title, 48)}: {ins.url}")
    return lines


def build_linkedin_context_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Notion용 링크드인 최적화 컨텍스트 (포스트 + Gemini 2×2 웹툰 프롬프트)."""
    hook1 = truncate(insights[0].korean_title, 55) if insights else "2026 AI 마케팅 핵심"
    post = build_linkedin_post_text(summary, insights)
    image_prompt = build_linkedin_image_prompt(insights)
    lines = [
        f"# LinkedIn 컨텍스트 — {hook1}",
        f"**날짜:** {stamp} · **용도:** 뉴스피드 포스트 (통합 컨텍스트)",
        "",
        "## 플랫폼 최적화 요약",
        "- **알고리즘:** 첫 2줄 훅 · dwell time · 댓글 CTA",
        "- **길이:** 1300자 이내",
        "- **링크:** 본문 URL 최소화 → 첫 댓글 배치",
        "- **이미지:** Gemini Nano Banana Pro 2 · 1:1 · 2×2 웹툰",
        "",
        "## 포스트 구조",
        f"**Line 1:** {hook1}",
        f"**Line 2:** 에이전트 도구 고르기 전에 프롬프트·SOP·측정 3가지만 잡아도 속도가 달라져요.",
        "",
        "**본문 요약:**",
        truncate(summary, 250),
        "",
        "**불릿:**",
    ]
    for ins in insights[:3]:
        lines.append(f"- → {truncate(ins.korean_title, 48)}: {truncate(ins.korean_summary, 80)}")
    lines.extend(
        [
            "",
            "## CTA",
            "이번 주 AI 마케팅 트렌드, 댓글로 공유해 주세요.",
            "",
            "## 해시태그",
            "#AIMarketing #AEO #AgenticAI #B2BMarketing #AX",
            "",
            "## 출처",
            *(_insight_source_lines(insights) or ["- (brief Top 인사이트 출처 URL)"]),
            "",
            "## 전체 포스트 초안",
            "```",
            post,
            "```",
            "",
            "## Gemini 이미지 생성 프롬프트 (1:1 · 2×2 웹툰)",
            "- **엔진:** `gemini-3-pro-image-preview` (Nano Banana Pro 2)",
            "- **비율:** 1:1 · 1080×1080 · 2K",
            "- **폰트:** Pretendard · Hangul speech bubble exact strings",
            "",
            "```",
            image_prompt,
            "```",
        ]
    )
    return "\n".join(lines)


def _table_cell(text: str, max_len: int = 80, *, max_sentences: int = 2) -> str:
    s = compress_sentences(str(text or "—"), max_len, max_sentences=max_sentences)
    return s.replace("|", "\\|").replace("\n", " ").strip()


def build_brief_excerpt_table(insights: list[Insight], stamp: str) -> str:
    """Unified Context — Research Brief 발췌 (Notion 표)."""
    count = min(len(insights), 7)
    lines = [
        "## Research Brief 발췌",
        "",
        f"**브리프 날짜:** `{stamp}` · **Top {count}**",
        "",
        "| # | 인사이트 | 핵심 요약 | 마케터 관점 | 출처 |",
        "|---:|---|---|---|---|",
    ]
    for i, ins in enumerate(insights[:7], 1):
        title = _table_cell(ins.korean_title, 56, max_sentences=1)
        summary = _table_cell(ins.context_blurb(max_chars=200, max_sentences=2), 200, max_sentences=2)
        view = _table_cell(
            ins.marketer_view or ins.korea_apply or ins.opportunity,
            140,
            max_sentences=2,
        )
        src = ins.url.strip() if ins.url else "—"
        lines.append(f"| {i} | {title} | {summary} | {view} | {src} |")
    return "\n".join(lines)


def build_unified_context_md(
    stamp: str,
    summary: str,
    insights: list[Insight],
    *,
    brief_excerpt: str = "",
) -> str:
    """채널 통합 컨텍스트 — Notion Daily Archive 인덱스용."""
    topic = insights[0].korean_title if insights else "주간 트렌드"
    lines = [
        f"# 통합 콘텐츠 컨텍스트 — {stamp}",
        "",
        "## SEO / AEO / GEO 공통 키",
        f"- **Primary topic:** {topic}",
        "- **Search intent:** B2B 마케터 · AX 전환 · AI 에이전트 실무",
        "- **AEO:** Direct Answer + FAQ 3+ · JSON-LD FAQPage",
        "- **GEO:** 출처 URL · 갱신일 · 인용 가능한 요약 블록",
        "",
        "## Executive Context",
        summary,
        "",
        "## 채널별 최적화 (요약)",
        "| 채널 | 포맷 | 핵심 |",
        "|------|------|------|",
        f"| Research | 심층 브리프 | Top {len(insights)} 인사이트 + 심층 분석 |",
        "| Blog | ~합니다 평문 | SEO/AEO/GEO · 출처 기반 확장 |",
        "| Instagram | 3장 정보형 캐러셀 | Gemini 4:5 · Hook → Insight → CTA |",
        "| LinkedIn | 1300자 | 2줄 훅 + 불릿 + 댓글 CTA |",
        "| Newsletter | md + HTML | TLDR · Hero · 모듈×3 · 단일 CTA · A/B 제목 |",
        "",
        "## Top 인사이트 (공통 소스)",
    ]
    for i, ins in enumerate(insights[:7], 1):
        blurb = ins.context_blurb(max_chars=180, max_sentences=2)
        lines.append(f"{i}. **{ins.korean_title}** — {blurb}")
    if insights:
        lines.extend(["", build_brief_excerpt_table(insights, stamp)])
    elif brief_excerpt:
        lines.extend(
            ["", "## Research Brief 발췌", compress_sentences(brief_excerpt, 1200, max_sentences=8)]
        )
    lines.extend(
        [
            "",
            "---",
            "아래 Notion 하위 페이지에서 카테고리별 전문을 확인하세요.",
        ]
    )
    return "\n".join(lines)


def build_notion_packages(
    stamp: str,
    brief_text: str,
    summary: str,
    insights: list[Insight],
    packages_dir: Path,
) -> dict[str, Path]:
    """Notion 아카이브용 카테고리별 단일 파일 생성."""
    packages_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "blog": packages_dir / f"{stamp}_blog-article.md",
        "instagram": packages_dir / f"{stamp}_instagram-context.md",
        "linkedin": packages_dir / f"{stamp}_linkedin-context.md",
        "unified": packages_dir / f"{stamp}_unified-context.md",
    }
    paths["blog"].write_text(build_blog_article_md(stamp, summary, insights), encoding="utf-8")
    paths["instagram"].write_text(
        build_instagram_context_md(stamp, summary, insights), encoding="utf-8"
    )
    paths["linkedin"].write_text(
        build_linkedin_context_md(stamp, summary, insights), encoding="utf-8"
    )
    paths["unified"].write_text(
        build_unified_context_md(
            stamp,
            summary,
            insights,
            brief_excerpt=compress_sentences(brief_text, 1200, max_sentences=8),
        ),
        encoding="utf-8",
    )
    return paths
