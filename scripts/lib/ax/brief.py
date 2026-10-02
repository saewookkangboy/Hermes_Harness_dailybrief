"""M1e Topic Brief 렌더링 — 렌즈별 슬롯 템플릿 (주제 무관 하드코딩 없음)."""
from __future__ import annotations

from typing import Any

from lib.ax.config import load_config
from lib.ax.evidence import Evidence, EvidencePack, select_top
from lib.ax.gates import GateReport
from lib.ax.text import clip, ieyo
from lib.ax.topic_spec import TopicSpec

LENS_VIEW = {
    "definition": (
        "{domain} 팀에 '{short}' 같은 개념 자료를 먼저 공유하면 용어 정렬에 드는 회의 시간이 줄어요.",
        "팀 위키에 한 장짜리 용어 정리로 옮겨 두고 신규 입사자 온보딩에도 써 보세요.",
    ),
    "market_news": (
        "'{short}' 소식은 {domain} 예산·우선순위 논의에서 바로 근거로 쓸 수 있는 시장 신호예요.",
        "이번 주 시장 모니터링 리포트에 한 줄 요약과 출처를 함께 남겨 보세요.",
    ),
    "tech_tools": (
        "'{short}'는 {domain} 자동화 후보예요. 기존 스택과 연동되는지부터 확인하는 게 순서예요.",
        "무료 플랜이나 데모로 1주 파일럿을 돌리고 작업 시간 변화를 기록해 보세요.",
    ),
    "use_cases": (
        "'{short}' 사례는 숫자로 된 성과가 있는지 먼저 봐요. 있으면 우리 KPI와 바로 비교할 수 있어요.",
        "사례의 측정 지표를 우리 팀 KPI 표에 매핑해 파일럿 목표로 잡아 보세요.",
    ),
    "risk_regulation": (
        "'{short}' 이슈는 도입 전에 법무·보안 검토 체크리스트에 꼭 넣어야 하는 항목이에요.",
        "승인 단계와 중단 기준(stop button)을 문서로 먼저 정해 두세요.",
    ),
    "korea": (
        "'{short}'는 국내 시장 맥락이라 해외 사례보다 내부 설득력이 커요.",
        "국내 고객·파트너 대상 콘텐츠와 제안서의 근거 자료로 인용해 보세요.",
    ),
    "future_signals": (
        "'{short}'는 아직 초기 신호예요. 지금 크게 투자하기보다 분기마다 추적할 대상이에요.",
        "Future Ahead 관찰 목록에 올려 두고 다음 분기에 변화를 다시 확인해 보세요.",
    ),
}
SOURCE_LABEL = {"web": "웹", "news": "뉴스", "github": "GitHub", "arxiv": "arXiv", "hn": "Hacker News"}


def short_title(title: str, n: int = 38) -> str:
    t = title.strip()
    if len(t) <= n:
        return t
    cut = t[:n].rsplit(" ", 1)[0]
    return cut if len(cut) >= n // 2 else t[:n]


def lens_label(lens: str, cfg: dict[str, Any]) -> str:
    return ((cfg.get("lenses") or {}).get(lens) or {}).get("label", lens)


def marketer_view(ev: Evidence, spec: TopicSpec) -> tuple[str, str]:
    view, use = LENS_VIEW.get(ev.lens, LENS_VIEW["definition"])
    return view.format(domain=spec.domain_label, short=short_title(ev.title)), use


def executive_summary(spec: TopicSpec, pack: EvidencePack, cfg: dict[str, Any]) -> list[str]:
    counts = pack.lens_counts()
    types = pack.source_type_counts()
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    missing = [lens_label(k, cfg) for k in (cfg.get("lenses") or {}) if not counts.get(k)]
    type_text = ", ".join(f"{SOURCE_LABEL.get(k, k)} {v}" for k, v in types.items())
    strongest = ", ".join(lens_label(k, cfg) for k, _ in ranked[:2]) or "없음"
    lines = [
        f"'{spec.ko_query}' 관련 근거 {pack.relevant_count}건을 {len(counts)}개 렌즈, {len(types)}종 소스({type_text})에서 모았어요.",
        f"근거가 가장 두터운 렌즈는 {ieyo(strongest)}.",
        f"근거가 비어 있는 렌즈는 {ieyo(', '.join(missing))}." if missing else "7개 렌즈 모두 근거가 있어요.",
    ]
    if pack.items:
        top = pack.items[0]
        lines.append(f"신뢰도가 가장 높은 신호는 '{short_title(top.title, 60)}'({top.domain}) 자료예요.")
    if pack.new_count() < pack.relevant_count:
        lines.append(f"이전 실행과 비교하면 새로 들어온 근거는 {pack.new_count()}건이에요.")
    return lines


def render_brief(spec: TopicSpec, pack: EvidencePack, report: GateReport | None = None, cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or load_config()
    n_top = int((cfg.get("evidence") or {}).get("top_insights", 7))
    top = select_top(pack, n_top)
    secondary = ", ".join(
        ((cfg.get("domains") or {}).get(d) or {}).get("label", d) for d in spec.secondary_domains
    )
    out = [
        f"# [Topic Research] {spec.keyword}",
        "",
        f"> {spec.stamp} · 도메인 {spec.domain_label} · 의도 {spec.intent_label} · 대상 {spec.audience}",
        "",
        "## Topic Spec",
        "",
        f"- **키워드:** {spec.keyword}",
        f"- **영문 검색어:** {spec.en_query}",
        f"- **핵심어 그룹:** {' / '.join(', '.join(g[:3]) for g in spec.core_groups)}",
        f"- **도메인:** {spec.domain_label}" + (f" (보조: {secondary})" if secondary else ""),
        f"- **의도:** {spec.intent_label}",
        "",
        "## Executive Summary",
        "",
        *[f"- {line}" for line in executive_summary(spec, pack, cfg)],
        "",
        "## 렌즈 커버리지",
        "",
        "| 렌즈 | 근거 수 | 대표 출처 |",
        "|------|--------|-----------|",
    ]
    counts = pack.lens_counts()
    for lens in cfg.get("lenses") or {}:
        rep = pack.by_lens(lens)
        out.append(f"| {lens_label(lens, cfg)} | {counts.get(lens, 0)} | {rep[0].domain if rep else '—'} |")
    out += ["", f"## Top {len(top)} 인사이트", ""]
    for i, ev in enumerate(top, 1):
        view, use = marketer_view(ev, spec)
        out += [
            f"### {i}. {ev.title}",
            "",
            f"- **렌즈:** {lens_label(ev.lens, cfg)}" + (" · 🆕 신규" if ev.is_new else ""),
            f"- **소스:** {SOURCE_LABEL.get(ev.source_type, ev.source_type)} · {ev.domain}" + (f" · {ev.published}" if ev.published else ""),
            f"- **신뢰도:** {ev.confidence_label} ({ev.confidence:.2f}) · 교차확인 {ev.corroboration}곳",
            f"- **요약:** {ev.snippet or '요약 없음.'}",
            f"- **마케터 관점:** {view}",
            f"- **활용 방법:** {use}",
            f"- **출처:** {ev.url}",
            "",
        ]
    out += [
        "## Evidence 목록",
        "",
        "| # | 렌즈 | 소스 | 제목 | 신뢰도 | URL |",
        "|---|------|------|------|--------|-----|",
    ]
    for i, ev in enumerate(pack.items[:25], 1):
        out.append(
            f"| {i} | {lens_label(ev.lens, cfg)} | {SOURCE_LABEL.get(ev.source_type, ev.source_type)} | "
            f"{clip(ev.title, 60).rstrip('.')} | {ev.confidence:.2f} | {ev.url} |"
        )
    out += [
        "",
        "## 수집 메타",
        "",
        f"- 쿼리 {pack.query_count}개 · 원본 {pack.raw_count}건 → 관련 {pack.relevant_count}건 ({pack.raw_ratio:.0%})",
        f"- 소스: {', '.join(f'{SOURCE_LABEL.get(k, k)} {v}' for k, v in pack.source_type_counts().items())}",
        f"- 도메인 {len(pack.domains())}개 · 수집 오류 {len(pack.errors)}건",
    ]
    if report:
        out.append(f"- 게이트: {report.summary()}")
    return "\n".join(out) + "\n"
