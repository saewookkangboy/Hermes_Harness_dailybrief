"""Research brief enrichment — 21년차 AI·AX 마케터 페르소나 + 확장 Insight 파이프라인."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from lib.common import compress_sentences, finish_at_sentence
from lib.content_quality import localize_title, polish_display_title
from lib.humanize_korean import humanize

INSIGHT_LIMIT = 7
CONFIG_PATH = Path.home() / "hermes-content-studio" / "config" / "research-brief.yaml"

TITLE_BY_TOPIC: dict[str, str] = {
    "korea_ax": "한국 AX 전환 — 교육·FAQ·사례 중심",
    "ax": "글로벌 AX(AI Transformation) 확산",
    "workspace_agents": "ChatGPT Workspace Agents 실무 검토",
    "llm_anthropic": "Claude 엔터프라이즈 — 거버넌스·컨텍스트",
    "llm_google": "Google Gemini — AEO·Workspace 연동",
    "llm_perplexity": "Perplexity·AI 검색(AEO) 최적화",
    "aeo": "2026 AEO(Answer Engine Optimization) 실무",
    "agent_marketing": "AI 에이전트·마케팅 자동화",
    "ai_governance": "AI 거버넌스·책임있는 AI",
    "ai_literacy": "AI 리터러시·조직 역량",
    "harness_engineering": "하네스·컨텍스트 엔지니어링",
    "hermes_agent": "Hermes Agent·자체호스팅 에이전트",
    "ai_ide": "AI IDE(Cursor·Windsurf) 실무",
    "ai_native": "AI Native 도입·파일럿 확대",
    "korea_adoption": "국내 B2B AI 도입·예산 승인",
}

PERSONA_INTRO = (
    "21년차 디지털 마케터(브랜드·콘텐츠·퍼포먼스·그로스·전략)이자, "
    "최근 4~5년 AI 리터러시·거버넌스·책임있는 AI 교육·컨설턴트입니다."
)


def expand_priority(template: str) -> str:
    today = date.today()
    return (
        template.replace("{year}", str(today.year))
        .replace("{ymd}", today.isoformat())
        .replace("{month}", f"{today.month:02d}")
    )


def load_priority_query_order() -> list[str]:
    today = date.today()
    default = [
        "digital marketing Korea AX transformation {year}",
        "Korea AX AI transformation news {year}",
        "South Korea enterprise AI adoption {year}",
        "OpenAI ChatGPT update {year} business marketing",
        "Anthropic Claude update {year} enterprise",
        "Google Gemini update {year} marketing",
        "Perplexity AI search update {year}",
        "AI governance responsible AI enterprise {year}",
        "AI literacy marketing team training {year}",
        "prompt engineering context engineering harness {year}",
        "Hermes agent NousResearch open source {year}",
        "AI agent marketing automation github {year}",
        "AEO answer engine optimization {year}",
    ]
    default = [q.replace("{year}", str(today.year)) for q in default]
    try:
        import yaml  # type: ignore

        if CONFIG_PATH.exists():
            cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
            pq = cfg.get("priority_queries") or {}
            ordered: list[str] = []
            if pq.get("korea"):
                ordered.append(expand_priority(pq["korea"]))
            ordered.extend(expand_priority(q) for q in (pq.get("llm") or []))
            for q in cfg.get("search_queries") or []:
                eq = expand_priority(str(q))
                if eq not in ordered:
                    ordered.append(eq)
            if ordered:
                return ordered
    except Exception:  # noqa: BLE001
        pass
    return default

RESEARCH_CATEGORIES: dict[str, str] = {
    "ax": "AX 트렌드·뉴스",
    "korea_ax": "대한민국 AX·AI 도입",
    "korea_adoption": "대한민국 AI 실무·도입 현황",
    "agent_marketing": "AI Agent·자동화",
    "workspace_agents": "LLM 서비스 — ChatGPT",
    "llm_anthropic": "LLM 서비스 — Claude",
    "llm_google": "LLM 서비스 — Gemini",
    "llm_perplexity": "LLM 서비스 — Perplexity",
    "aeo": "AI 마케팅 기술·AEO",
    "ai_ide": "AI 마케팅 기술·Repo·IDE",
    "ai_governance": "AI 리터러시·거버넌스",
    "ai_literacy": "AI 리터러시·교육",
    "harness_engineering": "하네스·컨텍스트·프롬프트 엔지니어링",
    "hermes_agent": "Hermes Agent·오픈소스",
    "ai_native": "AI Native·기업 적용",
    "instagram_algo": "소셜·콘텐츠 채널",
    "general": "AI 실무 적용·도입 현황",
}


def is_usable_search_result(item: dict) -> bool:
    """스팸·무관 Wikipedia 등 브리프에 부적합한 hit 제외."""
    url = (item.get("url") or "").strip()
    title = (item.get("title") or "").strip()
    snippet = (item.get("snippet") or "").strip()
    query = (item.get("query") or "").strip()
    if not url or not title:
        return False
    host = urlparse(url).netloc.lower()
    blocked = (
        "wikipedia.org",
        "filedot.",
        "bit.ly/",
        "tinyurl.com",
    )
    if any(b in host or b in url.lower() for b in blocked):
        return False
    blob = f"{title} {snippet}".lower()
    q = query.lower()
    if any(k in q for k in ("korea", "south korea", "ax")):
        if not any(
            k in blob
            for k in (
                "korea",
                "korean",
                "ax",
                "ai",
                "marketing",
                "enterprise",
                "adopt",
                "transform",
                "digital",
            )
        ):
            return False
    if len(title) < 10:
        return False
    return True


def classify_insight(title: str, snippet: str, query: str) -> str:
    q = query.lower()
    blob = f"{title} {snippet} {query}".lower()
    if "hermes" in q or "nousresearch" in q:
        return "hermes_agent"
    if "governance" in q or "responsible ai" in q:
        return "ai_governance"
    if "literacy" in q or ("training" in q and "ai" in q):
        return "ai_literacy"
    if "harness" in q or "context engineering" in q or "prompt engineering" in q:
        return "harness_engineering"
    if "anthropic" in q or "claude" in q:
        return "llm_anthropic"
    if "gemini" in q:
        return "llm_google"
    if "perplexity" in q:
        return "llm_perplexity"
    if "aeo" in q or "answer engine" in q:
        return "aeo"
    if "south korea enterprise" in q or "korea ax" in q:
        return "korea_adoption" if "adoption" in q else "korea_ax"
    if "digital marketing korea" in q or "korea ax" in blob:
        return "korea_ax"
    if "agent marketing" in q or "github" in q and "agent" in q:
        return "agent_marketing"
    if "hermes" in blob or "nousresearch" in blob:
        return "hermes_agent"
    if "governance" in blob or "responsible ai" in blob:
        return "ai_governance"
    if "literacy" in blob or "training" in blob and "ai" in blob:
        return "ai_literacy"
    if "harness" in blob or "context engineering" in blob or "prompt engineering" in blob:
        return "harness_engineering"
    if "anthropic" in blob or "claude" in blob:
        return "llm_anthropic"
    if "gemini" in blob and "google" in blob:
        return "llm_google"
    if "perplexity" in blob:
        return "llm_perplexity"
    if "korea" in blob or "south korea" in blob or "한국" in blob:
        if "ax" in blob or "transform" in blob:
            return "korea_ax"
        if "adopt" in blob or "enterprise" in blob:
            return "korea_adoption"
    if "ax" in blob or ("ai native" in blob and "transform" in blob):
        return "ax"
    if "workspace agent" in blob or ("chatgpt" in blob and "workspace" in blob):
        return "workspace_agents"
    if "openai" in blob or "chatgpt" in blob:
        return "workspace_agents"
    if "aeo" in blob or "answer engine" in blob:
        return "aeo"
    if "instagram" in blob and "algorithm" in blob:
        return "instagram_algo"
    if "cursor" in blob or "windsurf" in blob or "github" in blob or " sdk" in blob:
        return "ai_ide"
    if "agent" in blob or "automation" in blob:
        return "agent_marketing"
    if "adoption" in blob or "enterprise" in blob:
        return "ai_native"
    return "general"


def research_category_label(topic_key: str) -> str:
    return RESEARCH_CATEGORIES.get(topic_key, RESEARCH_CATEGORIES["general"])


def assess_trust(url: str) -> str:
    host = urlparse(url).netloc.lower()
    high = (
        "openai.com",
        "anthropic.com",
        "google.com",
        "blog.google",
        "cursor.com",
        "cxl.com",
        "kdi.re.kr",
        "lexology.com",
        "perplexity.ai",
        "github.com",
    )
    medium = ("reddit.com", "linkedin.com", "youtube.com", "quora.com", "community.openai.com")
    if any(d in host for d in high):
        return "high"
    if any(d in host for d in medium):
        return "medium"
    return "low"


def _persona_prefix() -> str:
    return PERSONA_INTRO


_BRIEF_GARBAGE_PATTERNS = (
    "관련 AI·마케팅 신호입니다",
    "관련 신호입니다",
    "재해석해 적용",
)


def polish_brief_prose(
    text: str,
    *,
    max_chars: int = 320,
    max_sentences: int = 3,
) -> str:
    """M1 brief 필드 — AI-tell 제거 + 완결 문장 (register 유지)."""
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw:
        return ""
    for garbage in _BRIEF_GARBAGE_PATTERNS:
        raw = raw.replace(garbage, "").strip()
    raw = re.sub(r"\s+", " ", raw).strip(" .")
    polished = humanize(raw, genre="brief").text
    out = compress_sentences(polished, max_chars, max_sentences=max_sentences)
    if out and out[-1] not in ".!?。…":
        out = finish_at_sentence(out, max_chars)
    return out


def build_executive_summary(
    period_label: str,
    enriched: list[dict],
    categories: list[str],
    themes: list[str],
) -> str:
    """Executive Summary — 페르소나 중복 없이 Top 축 요약."""
    theme = themes[0] if themes else "AX·에이전트"
    cats = ", ".join(categories[:5]) if categories else "AX·LLM·에이전트"
    raw = (
        f"일일 관측({period_label}) — 글로벌·대한민국 AI·마케팅 교차 신호입니다. "
        f"오늘 Top {len(enriched)} 축은 {cats} 등입니다. "
        f"특히 {theme}가 브랜드·콘텐츠·퍼포먼스·AX 로드맵에 연결됩니다. "
        f"LLM 4사, AI 거버넌스·리터러시, 하네스·Hermes Agent 실무를 "
        f"통합 컨텍스트로 정리했습니다."
    )
    return polish_brief_prose(raw, max_chars=480, max_sentences=4)


def synthesize_korean_summary(title: str, snippet: str, query: str) -> str:
    """내용 요약 — 영문 스니펫 → 한국어 2~3문장."""
    key = classify_insight(title, snippet, query)
    ko_title = localize_title(title)

    summaries: dict[str, str] = {
        "korea_ax": (
            f"[대한민국] {ko_title} 관련 신호입니다. "
            f"국내 기업 AX(AI Transformation) 전환이 가속되면서 "
            f"운영·마케팅·교육 전 영역에 AI 통합을 검토하지 않으면 "
            f"경쟁력 격차가 벌어질 수 있습니다. "
            f"글로벌 AX 사례와 국내 regulation·legacy 환경을 함께 봐야 합니다."
        ),
        "ax": (
            f"[글로벌 AX] {ko_title} — AI Transformation이 산업 전반으로 "
            f"확산 중입니다. PoC를 넘어 조직·프로세스·데이터·인력 역량을 "
            f"동시에 재설계하는 단계로 진입하고 있습니다."
        ),
        "agent_marketing": (
            f"[AI Agent·자동화] 2026년 'AI agent' 라벨은 과장되는 경우가 많습니다. "
            f"마케팅 팀은 빌더·플랫폼보다 반복 업무 use case 정의가 먼저입니다. "
            f"프롬프트·SOP·측정·거버넌스를 선행해야 ROI를 설명할 수 있습니다."
        ),
        "workspace_agents": (
            f"[ChatGPT·OpenAI] Workspace Agents는 팀 협업 맥락 에이전트 실험의 "
            f"신호입니다. Pro 플랜 한계와 기대 대비 성능 갭에 대한 "
            f"현장 피드백이 공존하므로 파일럿 검증이 필수입니다."
        ),
        "llm_anthropic": (
            f"[Claude·Anthropic] 엔터프라이즈·마케팅 워크플로에 Claude를 "
            f"포함하는 팀이 늘고 있습니다. 긴 컨텍스트·안전 정책·"
            f"에이전트 API 업데이트를 거버넌스 관점에서 함께 봐야 합니다."
        ),
        "llm_google": (
            f"[Gemini·Google] Gemini 멀티모달·Workspace·검색 연동 업데이트는 "
            f"AEO·콘텐츠·자동화 파이프라인에 영향을 줍니다. "
            f"Google 생태계 의존 팀은 변경 로그 추적이 필요합니다."
        ),
        "llm_perplexity": (
            f"[Perplexity] Answer Engine·실시간 검색형 AI는 AEO·브랜드 인용 "
            f"전략과 직결됩니다. 출처·신선도·권위 신호가 "
            f"Perplexity 노출에 특히 중요합니다."
        ),
        "aeo": (
            f"[AEO] Answer Engine(ChatGPT·Perplexity·Gemini)은 FAQ·Direct Answer·"
            f"출처·갱신일을 선호합니다. SEO를 대체하지 않고 AI 답변 레이어를 "
            f"추가하는 2026년 표준 전략입니다."
        ),
        "ai_governance": (
            f"[AI 거버넌스] 책임있는 AI·데이터·프라이버시·모델 사용 정책이 "
            f"마케팅 자동화·에이전트 도입의 전제 조건이 되었습니다. "
            f"거버넌스 없는 에이전트 확산은 브랜드·법무 리스크로 이어집니다."
        ),
        "ai_literacy": (
            f"[AI 리터러시] 마케팅·콘텐츠·퍼포먼스 팀의 AI 역량 격차가 "
            f"도입 속도를 좌우합니다. 프롬프트·검증·한계 이해 교육이 "
            f"AX 로드맵의 숨은 병목입니다."
        ),
        "harness_engineering": (
            f"[하네스·컨텍스트·프롬프트] 프롬프트 엔지니어링을 넘어 "
            f"컨텍스트 엔지니어링·하네스 엔지니어링으로 에이전트 운영이 "
            f"성숙하고 있습니다. 결정적 파이프라인 + 선택적 LLM polish가 "
            f"비용·품질·재현성의 균형점입니다."
        ),
        "hermes_agent": (
            f"[Hermes Agent] 오픈소스·자체호스팅 에이전트는 "
            f"멀티채널·스킬·메모리 확장이 강점입니다. "
            f"Intel Mac·VPS 등 로컬/엣지 운영으로 데이터 주권·"
            f"커스터마이징이 가능합니다."
        ),
        "ai_ide": (
            f"[AI IDE·Repo] Cursor·Windsurf·GitHub 연동은 "
            f"바이브 코딩·에이전트 SDK로 마케팅 자동화·"
            f"콘텐츠 도구 제작 속도를 높입니다."
        ),
        "ai_native": (
            f"[AI Native·도입] 기업 AI 도입은 파일럿→검증→확대 사이클로 "
            f"짧아지고 있습니다. '선언'보다 측정 가능한 use case가 "
            f"구매·교육 의사결정을 좌우합니다."
        ),
    }
    return polish_brief_prose(
        summaries.get(
            key,
            f"{ko_title} — 글로벌·국내 AI·마케팅 교차 신호입니다. "
            f"브랜드·퍼포먼스·콘텐츠·AX 관점에서 재해석할 여지가 있습니다.",
        ),
        max_chars=280,
        max_sentences=3,
    )


def synthesize_insight_derivation(
    topic_key: str, title: str, summary_ko: str = ""
) -> str:
    """Insight 도출 — So What."""
    ko = polish_display_title(title)
    insights: dict[str, str] = {
        "korea_ax": (
            "국내 AX는 '언제'보다 '어디서 손대느냐'가 핵심입니다. "
            "PoC·선언보다 FAQ·교육·사례로 수요를 끌어당기는 단계입니다."
        ),
        "agent_marketing": (
            "에이전트 도구 경쟁보다 '반복 업무 3개 + SOP + KPI' 정의가 "
            "2026년 마케팅 조직의 승부처입니다."
        ),
        "workspace_agents": (
            "ChatGPT Workspace Agents는 '만능 비서'가 아니라 "
            "협업 맥롽 자동화 레이어로 재정의해야 기대치 관리가 됩니다."
        ),
        "aeo": (
            "검색 트래픽은 AEO(AI 인용)와 SEO가 분리되지 않습니다. "
            "FAQ·Direct Answer·GEO가 하나의 콘텐츠 자산입니다."
        ),
        "ai_governance": (
            "에이전트 확산 속도는 기술보다 거버넌스·리터러시가 병목입니다. "
            "책임있는 AI는 컴플라이언스가 아니라 브랜드 신뢰 자산입니다."
        ),
        "harness_engineering": (
            "LLM 전체 재생성보다 결정적 하네스 + 검증 게이트가 "
            "콘텐츠·마케팅 파이프라인 비용을 통제합니다."
        ),
        "hermes_agent": (
            "클라우드 에이전트만으로는 데이터·채널 커스터마이징 한계가 있습니다. "
            "Hermes류 자체호스팅이 AX·AI Native 로드맵의 대안축입니다."
        ),
        "llm_anthropic": (
            "Claude 도입은 안전·정책·컨텍스트 윈도우를 거버넌스 체크리스트와 "
            "함께 봐야 멀티 LLM 전략의 한 축이 됩니다."
        ),
        "llm_google": (
            "Gemini·Google 검색·Workspace 변경은 AEO·콘텐츠 갱신 주기와 "
            "연동해 모니터링해야 합니다."
        ),
        "llm_perplexity": (
            "Perplexity 노출은 출처 URL·갱신일·FAQ 구조가 핵심입니다. "
            "브랜드 GEO 실험장으로 쓰기 좋습니다."
        ),
        "korea_adoption": (
            "국내 B2B는 기술 데모보다 직군별 use case 워크숍이 "
            "예산 승인 속도를 좌우합니다."
        ),
    }
    if topic_key in insights:
        return insights[topic_key]
    lead = compress_sentences(summary_ko, 140, max_sentences=2) if summary_ko else ko
    return (
        f"{lead} "
        f"이 신호는 국내 실무 FAQ와 채널 재가공으로 연결할 수 있습니다."
    )


def synthesize_marketer_view(topic_key: str, title: str, channel: str) -> str:
    """21년차 마케터·AX 컨설턴트 — 1인칭 현장 서술."""
    views: dict[str, str] = {
        "korea_ax": (
            "저는 컨설팅 현장에서 PoC만 강조할 때 구매가 막히는 패턴을 반복 봅니다. "
            "임원·실무자 FAQ를 분리해 '우리 조직에 무엇이 바뀌는지'부터 설명하면 "
            "교육·컨설팅 리드와 브랜드 신뢰가 동시에 쌓입니다."
        ),
        "korea_adoption": (
            "국내 B2B 도입 현장에서는 '기술 데모'보다 직군별 use case 워크숍이 "
            "예산 승인 속도를 좌우합니다. 저는 adoption 지표를 PoC 전에 "
            "교육·FAQ 완료율로 먼저 잡습니다."
        ),
        "ax": (
            "21년간 브랜드·퍼포먼스·그로스를 오가며 느낀 건, AX가 채널 전략과 "
            "별개가 아니라는 점입니다. AEO·에이전트·콘텐츠 자동화를 하나의 "
            "AI Native 로드맵으로 묶어 KPI에 연결해야 합니다."
        ),
        "agent_marketing": (
            "현장에서 퍼포먼스·CRM·리포팅처럼 하루 30분 이상 쓰는 반복 업무부터 "
            "에이전트 후보를 매핑합니다. hype 비교표보다 실습형 콘텐츠가 "
            "B2B 신뢰와 리드를 동시에 만듭니다."
        ),
        "workspace_agents": (
            "OpenAI 공식 메시지와 Reddit 현장 의견의 간극을 교육·컨설팅 소재로 "
            "투명하게 공유하면, 저는 구매 지연을 줄이는 데 효과적이었습니다."
        ),
        "llm_anthropic": (
            "Claude 도입 시 저는 안전·정책·컨텍스트 윈도우를 "
            "거버넌스 체크리스트에 넣습니다. 멀티 LLM 전략의 한 축입니다."
        ),
        "llm_google": (
            "Gemini·Google 검색·Workspace 변경은 AEO·콘텐츠 갱신 주기와 "
            "연동해 모니터링하는 게 제 실무 루틴입니다."
        ),
        "llm_perplexity": (
            "Perplexity 인용은 출처 URL·갱신일·FAQ 구조가 핵심입니다. "
            "브랜드 GEO 전략 실험장으로 쓰기 좋습니다."
        ),
        "aeo": (
            "키워드 나열형 블로그를 줄이고 '질문 하나·답 하나' Direct Answer와 "
            "JSON-LD FAQ를 세트로 배포하라고 팀에 권합니다."
        ),
        "ai_governance": (
            "에이전트·자동화 도입 전 데이터 분류·승인·로그 정책을 "
            "마케팅 ops에 포함해야 합니다. 책임있는 AI는 차별화 포인트입니다."
        ),
        "ai_literacy": (
            "팀 AI 리터러시는 '프롬프트 작성'을 넘어 출력 검증·한계 인지·"
            "윤리적 사용까지 포함해야 AX 속도가 납니다."
        ),
        "harness_engineering": (
            "콘텐츠·리서치·소셜 파이프라인은 하네스(결정적 조립) + "
            "선택적 LLM polish로 설계합니다. 재현성이 브랜드 품질입니다."
        ),
        "hermes_agent": (
            "Hermes Agent는 Telegram·Notion·콘텐츠 스튜디오처럼 "
            "멀티채널 커맨더 패턴에 적합합니다. 자체호스팅 AX 사례로 강의화하세요."
        ),
        "ai_ide": (
            "콘텐츠 기획(Hermes) → Cursor 구현 핸드오프는 "
            "비개발 마케터의 AI Native 역량 지표로 봅니다."
        ),
        "ai_native": (
            "AI Native는 도구 도입이 아니라 측정·SOP·거버넌스가 "
            "갖춰진 조직 설계입니다."
        ),
    }
    base = views.get(
        topic_key,
        f"{localize_title(title)} 주제는 FAQ·실습·강의로 "
        f"국내 B2B 전환에 맞게 재구성하라고 현장에서 권합니다.",
    )
    if channel == "lecture":
        return base.replace("블로그", "강의").replace("LinkedIn", "워크숍")
    return base


def synthesize_utilization(topic_key: str, channel: str) -> str:
    """활용 방법 — 브랜드·콘텐츠·퍼포먼스·AX 적용."""
    utils: dict[str, str] = {
        "korea_ax": (
            "① AX 타임라인 1페이지 ② 직군별 FAQ 5개 ③ 강의·컨설팅 랜딩 연결. "
            "브랜드 스토리와 퍼포먼스 리드 gen을 분리 운영하세요."
        ),
        "agent_marketing": (
            "① 반복 업무 3개 목록 ② use case→빌더 매핑표 ③ 2주 파일럿 KPI. "
            "그로스·CRM·리포팅 팀별로 SOP를 표준화하세요."
        ),
        "workspace_agents": (
            "① 협업 시나리오 2~3개 정의 ② Pro 한계 문서화 ③ 기대 vs 현실 리포트. "
            "내부 교육·LinkedIn 투명 공유로 신뢰를 쌓으세요."
        ),
        "aeo": (
            "① Direct Answer 문단 ② FAQ JSON-LD ③ 갱신일·출처 블록. "
            "blog HTML과 packages 평문 FAQ를 동기화하세요."
        ),
        "ai_governance": (
            "① 데이터 분류·승인 매트릭스 ② 에이전트 로그·감사 ③ "
            "책임있는 AI 교육 모듈. 법무·브랜드·마케팅 ops 공동 워크숍."
        ),
        "harness_engineering": (
            "① brief→assemble 결정적 파이프라인 ② validate-output 게이트 "
            "③ HERMES_ENHANCE=1 선택 polish. Hermes Content Studio가 레퍼런스."
        ),
        "hermes_agent": (
            "① Intel Mac/VPS 자체호스팅 ② Telegram·Notion 커맨더 "
            "③ 스킬·MCP 확장. 콘텐츠·리서치·아카이브 자동화 데모."
        ),
        "llm_anthropic": "Claude를 장문 분석·정책 민감 초안·에이전트 API 축으로 편성.",
        "llm_google": "Gemini를 멀티모달·Workspace·AEO 실험 축으로 편성.",
        "llm_perplexity": "Perplexity 인용 모니터링 + FAQ·출처 강화 A/B.",
    }
    ch = channel.split("|")[0].strip()
    suffix = {
        "blog": "블로그 Direct Answer + SEO/AEO/GEO 통합.",
        "linkedin": "2줄 훅 + 불릿 + 2×2 웹툰 이미지.",
        "instagram": "3장 웹툰 캐러셀(Gemini 1:1).",
        "lecture": "실습·워크숍·AX 로드맵 강의 모듈.",
    }.get(ch, "통합 컨텍스트 1회 → 채널별 재가공.")
    return f"{utils.get(topic_key, 'FAQ·실습·사례 3종 세트로 B2B 전환.')} {suffix}"


def synthesize_guides_tips(topic_key: str) -> str:
    """가이드·팁 — 실무 체크리스트."""
    tips: dict[str, str] = {
        "korea_ax": "Tip: regulation·legacy 이슈를 타임라인 FAQ에 선제 포함. '왜 지금' 3 bullet.",
        "agent_marketing": "Tip: 빌더 비교 전 '우리 팀 반복 업무 3개' 워크숩. KPI는 시간 절감·오류율.",
        "workspace_agents": "Tip: '에이전트에게 맡길 것/사람이 확인할 것' 목록 분리. 2주 파일럿 필수.",
        "aeo": "Tip: FAQ 3+ · JSON-LD · '업데이트: YYYY-MM-DD' 3곳 동일 표기.",
        "ai_governance": "Tip: PII·브랜드 가이드·모델 사용 정책을 에이전트 SOP에 embed.",
        "ai_literacy": "Tip: 프롬프트·검증·한계·윤리 4주 커리큘럼. 실습은 내부 데이터로.",
        "harness_engineering": (
            "Tip: prompt→context→harness 순 성숙. "
            "결정적 assemble + validate-output + 선택 LLM polish."
        ),
        "hermes_agent": "Tip: hermes-cli only 마스킹 · Notion 100% sync · Telegram Permalink.",
        "llm_perplexity": "Tip: Perplexity에 인용되는 문장을 Direct Answer로 A/B 테스트.",
    }
    return tips.get(
        topic_key,
        "Tip: 글로벌 신호 1건 → 한국 FAQ 1건 → LinkedIn 불릿 1건 동일 메시지 유지.",
    )


def synthesize_korea_apply(topic_key: str, channel: str) -> str:
    applies: dict[str, str] = {
        "korea_ax": (
            "국내 B2B는 PoC보다 교육·FAQ·사례로 구매 전 검증. "
            "KDI·Lexology·국내 AX 세미나 수요와 연계."
        ),
        "agent_marketing": (
            "영어 tutorial 복붙보다 한국어 FAQ + 내부 예시 데이터 실습. "
            "에이전시·인하우스 공통 SOP 템플릿 제공."
        ),
        "ai_governance": (
            "국내 개인정보·AI 기본법 맥락에서 거버넌스 교육 수요 증가. "
            "책임있는 AI를 브랜드 차별화로 포지셔닝."
        ),
        "harness_engineering": (
            "Hermes Content Studio·awesome-harness-engineering 패턴을 "
            "국내 AX·콘텐츠 팀 교육 소재로 로컬라이즈."
        ),
    }
    return applies.get(
        topic_key,
        "글로벌 사례를 국내 AX·에이전트 FAQ·강의·LinkedIn으로 재가공.",
    )


def synthesize_market_impact(topic_key: str, channel: str) -> str:
    impacts: dict[str, str] = {
        "korea_ax": "국내 AX·디지털 전환 예산 + 교육·컨설팅 구매 동반 증가.",
        "agent_marketing": "마케팅 자동화·에이전트 빌더 비교 수요 급증(Reddit·LinkedIn).",
        "ai_governance": "책임있는 AI·거버넌스 교육 RFP·워크숍 수요 확대.",
        "ai_literacy": "마케팅·콘텐츠·퍼포먼스 팀 AI 역량 교육 수요.",
        "harness_engineering": "결정적 AI 파이프라인·하네스 패턴 커뮤니티 확산.",
        "llm_perplexity": "Answer Engine·GEO 투자가 SEO와 분리되지 않음.",
    }
    ch_note = {
        "blog": "Direct Answer·AEO 수요.",
        "linkedin": "인사이트·댓글 CTA 수요.",
        "instagram": "저장형 캐러셀 수요.",
        "lecture": "AX·에이전트 실습 강의 수요.",
    }.get(channel.split("|")[0].strip(), "B2B 의사결정 연계.")
    return f"{impacts.get(topic_key, 'B2B AI·마케팅 교육 시장 수요.')} {ch_note}"


def synthesize_opportunity(topic_key: str, channel: str) -> str:
    opps: dict[str, str] = {
        "korea_ax": "Direct Answer + LinkedIn + Instagram FAQ 3종",
        "agent_marketing": "반복 업무 매핑 실습 + LinkedIn + 강의",
        "ai_governance": "거버넌스 체크리스트 + 책임있는 AI 워크숍",
        "harness_engineering": "하네스 실습 강의 + 블로그 케이스 스터디",
        "hermes_agent": "자체호스팅 데모 + Telegram 커맨더 강의",
    }
    return f"{opps.get(topic_key, '통합 컨텍스트 → 채널 재가공')} ({channel.replace(' ', '')})"


def build_llm_platform_pulse(enriched: list[dict]) -> str:
    """LLM 4사 펄스 — 수집 결과 기반 (없으면 관측 메모)."""
    platforms = {
        "OpenAI · ChatGPT": ["workspace_agents", "openai"],
        "Anthropic · Claude": ["llm_anthropic", "claude", "anthropic"],
        "Google · Gemini": ["llm_google", "gemini"],
        "Perplexity": ["llm_perplexity", "perplexity"],
    }
    lines = ["### LLM 플랫폼 펄스 (일일 관측)", ""]
    for label, keys in platforms.items():
        matched = [
            e for e in enriched
            if e["topic_key"] in keys
            or any(k in (e.get("title") or "").lower() for k in keys)
        ]
        if matched:
            e = matched[0]
            pulse = compress_sentences(e["insight_derivation"], 160, max_sentences=2)
            src_title = polish_display_title(e.get("korean_title") or e.get("title") or "")
            lines.append(f"- **{label}:** {pulse} (출처: {src_title})")
        else:
            lines.append(
                f"- **{label}:** 금일 수집 결과에 직접 매칭 없음 — "
                f"주간 changelog·공식 블로그 2차 확인 권장."
            )
    lines.append("")
    return "\n".join(lines)


def build_coverage_table(enriched: list[dict]) -> str:
    """리서치 커버리지 매트릭스."""
    pillars = [
        ("AI 마케팅 기술·Repo", ["aeo", "ai_ide", "hermes_agent"]),
        ("LLM 서비스 업데이트", ["workspace_agents", "llm_anthropic", "llm_google", "llm_perplexity"]),
        ("AX·AI Native", ["ax", "korea_ax", "ai_native"]),
        ("AI 리터러시·거버넌스", ["ai_literacy", "ai_governance"]),
        ("에이전트·하네스·엔지니어링", ["agent_marketing", "harness_engineering", "hermes_agent"]),
    ]
    lines = [
        "### 리서치 커버리지 (오늘의 렌즈)",
        "",
        "| 영역 | 관측 | 대표 인사이트 |",
        "|------|------|--------------|",
    ]
    for label, keys in pillars:
        matched = [e for e in enriched if e["topic_key"] in keys]
        if matched:
            e = matched[0]
            cell = compress_sentences(e["korean_title"], 48, max_sentences=1)
            lines.append(f"| {label} | ✅ | {cell} |")
        else:
            lines.append(f"| {label} | — | 2차 수집 권장 |")
    lines.append("")
    return "\n".join(lines)


def build_engineering_highlights(enriched: list[dict]) -> str:
    """프롬프트·컨텍스트·하네스 하이라이트."""
    keys = {"harness_engineering", "hermes_agent", "agent_marketing", "ai_ide"}
    matched = [e for e in enriched if e["topic_key"] in keys]
    lines = [
        "### 실무 가이드 하이라이트 (프롬프트·컨텍스트·하네스·에이전트)",
        "",
        "- **프롬프트 엔지니어링:** 반복 업무 단위별 템플릿 + 검증 체크리스트",
        "- **컨텍스트 엔지니어링:** brief·handoff·통합 컨텍스트 단일 소스",
        "- **하네스 엔지니어링:** assemble → validate → archive 결정적 파이프라인",
        "- **Hermes Agent / AI Agent:** 멀티채널 커맨더 · 스킬 · Notion sync",
        "",
    ]
    for e in matched[:3]:
        lines.append(f"- {e['guides_tips']}")
    lines.append("")
    return "\n".join(lines)


def enrich_insight(item: dict, used_views: set[str] | None = None) -> dict:
    title = (item.get("title") or "").strip()
    snippet = (item.get("snippet") or "").strip()
    query = (item.get("query") or "").strip()
    url = (item.get("url") or "").strip()
    topic_key = classify_insight(title, snippet, query)
    channel = item.get("channel") or ""
    summary_ko = synthesize_korean_summary(title, snippet, query)
    marketer_view = synthesize_marketer_view(topic_key, title, channel)
    if used_views is not None:
        if marketer_view in used_views:
            suffix = compress_sentences(polish_display_title(title), 40, max_sentences=1)
            marketer_view = f"{marketer_view} ({suffix} 맥락에서 우선순위를 재정렬합니다.)"
        used_views.add(marketer_view)

    return {
        **item,
        "topic_key": topic_key,
        "research_category": research_category_label(topic_key),
        "korean_title": TITLE_BY_TOPIC.get(topic_key) or polish_display_title(title),
        "summary_ko": summary_ko,
        "insight_derivation": synthesize_insight_derivation(topic_key, title, summary_ko),
        "marketer_view": marketer_view,
        "utilization": synthesize_utilization(topic_key, channel),
        "guides_tips": synthesize_guides_tips(topic_key),
        "korea_apply": synthesize_korea_apply(topic_key, channel),
        "market_impact": synthesize_market_impact(topic_key, channel),
        "opportunity": synthesize_opportunity(topic_key, channel),
        "trust": assess_trust(url),
    }
