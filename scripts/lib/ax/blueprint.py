"""M2 AX Blueprint — 마케팅 가치사슬 × 자동화 기회 매트릭스 · 성숙도 · HITL · KPI · 30/60/90."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lib.ax.config import load_config
from lib.ax.evidence import Evidence, EvidencePack, term_hits
from lib.ax.topic_spec import TopicSpec

QUADRANTS = {
    "quick_win": "Quick Win",
    "strategic": "전략 과제",
    "efficiency": "효율 개선",
    "hold": "보류",
}
GOVERNED_STAGES = {"production", "distribution", "optimization"}


def _quadrant(impact: int, feasibility: int) -> str:
    if impact >= 4 and feasibility >= 4:
        return "quick_win"
    if impact >= 4:
        return "strategic"
    if feasibility >= 4:
        return "efficiency"
    return "hold"


def _clamp(v: int) -> int:
    return max(1, min(5, v))


def _risk_text(stage: str, pack: EvidencePack, risk_titles: list[str]) -> str:
    if risk_titles and stage in GOVERNED_STAGES:
        return f"'{risk_titles[0]}' 같은 규제·신뢰 이슈를 발행 전 체크리스트로 관리해야 해요"
    if stage in ("measurement", "optimization"):
        return "개인정보·동의 범위를 벗어난 데이터 결합이 없는지 점검해야 해요"
    return "근거 출처가 불분명한 자동 생성 결과가 그대로 쓰이지 않게 사실 확인 단계를 둬야 해요"


def _stage_fit(ev: Evidence, scfg: dict[str, Any]) -> float:
    boost = set(scfg.get("lens_boost") or [])
    text = f"{ev.title} {ev.snippet}".lower()
    return (
        3 * term_hits(scfg.get("evidence_terms") or [], text)
        + 2 * (ev.lens in boost)
        + len(set(ev.lenses) & boost)
        + ev.confidence
    )


def _assign_evidence(order: list[str], chain: dict[str, Any], pack: EvidencePack, per_stage: int = 2) -> dict[str, list[Evidence]]:
    """우선순위 높은 단계부터 적합도 순으로 근거를 배정. 이미 인용한 근거는 후순위로 밀어 중복 인용을 줄인다."""
    used: set[str] = set()
    out: dict[str, list[Evidence]] = {}
    for stage in order:
        scfg = chain[stage]
        boost = set(scfg.get("lens_boost") or [])
        candidates = [ev for ev in pack.items if boost & set(ev.lenses) or term_hits(scfg.get("evidence_terms") or [], f"{ev.title} {ev.snippet}".lower())]
        candidates.sort(key=lambda ev: (ev.id not in used, _stage_fit(ev, scfg)), reverse=True)
        out[stage] = candidates[:per_stage]
        used.update(ev.id for ev in out[stage])
    return out


def build_blueprint(spec: TopicSpec, pack: EvidencePack, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    counts = pack.lens_counts()
    impact_table = (cfg.get("domain_stage_impact") or {}).get(spec.domain) or (
        cfg.get("domain_stage_impact") or {}
    ).get("general_marketing", {})
    catalog = cfg.get("tool_catalog") or {}
    domain_tools = [t for d in [spec.domain, *spec.secondary_domains] for t in (cfg.get("domain_tools") or {}).get(d, [])]
    tech_signal = counts.get("tech_tools", 0) + len(pack.by_source("github"))
    risk_items = pack.by_lens("risk_regulation")
    risk_titles = [ev.title for ev in risk_items[:2]]

    chain = cfg.get("value_chain") or {}
    boosts = {s: sum(counts.get(lens, 0) for lens in c.get("lens_boost") or []) for s, c in chain.items()}
    mean_boost = sum(boosts.values()) / len(boosts) if boosts else 0.0
    proven = counts.get("use_cases", 0) >= 2

    opportunities: list[dict[str, Any]] = []
    for stage, scfg in chain.items():
        lens_boost = scfg.get("lens_boost") or []
        impact = _clamp(int(impact_table.get(stage, 3)) + (1 if boosts[stage] >= 1.5 * mean_boost > 0 else 0))
        own_tools = [t for t in domain_tools if t.get("stage") == stage]
        stage_tools = own_tools + list(catalog.get(stage) or [])
        feasibility = (
            2
            + (1 if tech_signal >= 3 else 0)
            + (1 if own_tools else 0)
            + (1 if proven and "use_cases" in lens_boost else 0)
            - (1 if len(risk_items) >= 2 and stage in GOVERNED_STAGES else 0)
        )
        feasibility = _clamp(feasibility)
        quadrant = _quadrant(impact, feasibility)
        target = "L3" if quadrant == "quick_win" and tech_signal >= 2 else "L2"
        opportunities.append(
            {
                "stage": stage,
                "label": scfg.get("label", stage),
                "impact": impact,
                "feasibility": feasibility,
                "priority": impact * feasibility,
                "quadrant": quadrant,
                "quadrant_label": QUADRANTS[quadrant],
                "automation": f"{scfg.get('automation', '')} — '{spec.ko_query}' 기준으로 설계해요",
                "kpi": scfg.get("kpi", ""),
                "hitl": scfg.get("hitl", ""),
                "risk": _risk_text(stage, pack, risk_titles),
                "maturity_current": "L1",
                "maturity_target": target,
                "tools": [t["name"] for t in stage_tools[:3]],
            }
        )
    ranked = sorted(opportunities, key=lambda o: o["priority"], reverse=True)
    refs = _assign_evidence([o["stage"] for o in ranked], chain, pack)
    for o in opportunities:
        o["evidence"] = [{"title": ev.title, "url": ev.url} for ev in refs[o["stage"]]]
    quick = [o for o in ranked if o["quadrant"] == "quick_win"]
    strategic = [o for o in ranked if o["quadrant"] == "strategic"]
    rest = [o for o in ranked if o not in quick and o not in strategic]
    roadmap = {
        "30": [o["label"] for o in (quick or ranked)[:2]],
        "60": [o["label"] for o in (quick[2:] + strategic)[:2]] or [o["label"] for o in ranked[2:4]],
        "90": [o["label"] for o in (strategic[2:] + rest)[:2]] or [o["label"] for o in ranked[4:6]],
    }
    target_overall = "L3" if sum(o["maturity_target"] == "L3" for o in opportunities) >= 2 else "L2"
    return {
        "topic": spec.keyword,
        "stamp": spec.stamp,
        "domain": spec.domain_label,
        "maturity": {"current": "L1", "target": target_overall, "assumption": "현재 수준은 일반적인 마케팅 팀 기준 가정치예요"},
        "opportunities": ranked,
        "roadmap": roadmap,
        "governance": [
            "모든 자동 발행에는 사람이 누르는 중단 버튼(stop button)을 둬요",
            "생성 결과는 출처 URL과 함께 저장해 사후 감사가 가능하게 해요",
            *([f"주의 이슈: {t}" for t in risk_titles]),
        ],
    }


def render_blueprint(bp: dict[str, Any], cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or load_config()
    levels = cfg.get("maturity_levels") or {}
    m = bp["maturity"]
    out = [
        f"# [AX Blueprint] {bp['topic']}",
        "",
        f"> {bp['stamp']} · 도메인 {bp['domain']} · 성숙도 {m['current']} → {m['target']}",
        "",
        "## AX 성숙도",
        "",
        f"- **현재:** {m['current']} {levels.get(m['current'], {}).get('label', '')} — {levels.get(m['current'], {}).get('desc', '')}",
        f"- **목표:** {m['target']} {levels.get(m['target'], {}).get('label', '')} — {levels.get(m['target'], {}).get('desc', '')}",
        f"- {m['assumption']}.",
        "",
        "## 자동화 기회 매트릭스",
        "",
        "| 가치사슬 | 영향도 | 실행 가능성 | 구분 | 목표 레벨 | 추천 도구 |",
        "|----------|--------|-------------|------|-----------|-----------|",
    ]
    for o in bp["opportunities"]:
        out.append(
            f"| {o['label']} | {o['impact']} | {o['feasibility']} | {o['quadrant_label']} | {o['maturity_target']} | {', '.join(o['tools']) or '—'} |"
        )
    out += ["", "## 단계별 설계", ""]
    for o in bp["opportunities"]:
        out += [
            f"### {o['label']} · {o['quadrant_label']}",
            "",
            f"- **자동화:** {o['automation']}.",
            f"- **KPI:** {o['kpi']}",
            f"- **HITL:** {o['hitl']}.",
            f"- **리스크:** {o['risk']}.",
        ]
        for ev in o["evidence"]:
            out.append(f"- **근거:** {ev['title']} — {ev['url']}")
        out.append("")
    out += ["## 30/60/90일 로드맵", ""]
    for day, items in bp["roadmap"].items():
        out.append(f"- **{day}일:** {', '.join(items) or '—'}")
    out += ["", "## 거버넌스", ""]
    out += [f"- {g}." if not g.endswith(".") else f"- {g}" for g in bp["governance"]]
    return "\n".join(out) + "\n"


def write_blueprint(bp: dict[str, Any], md_path: Path, json_path: Path) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_blueprint(bp), encoding="utf-8")
    json_path.write_text(json.dumps(bp, ensure_ascii=False, indent=2), encoding="utf-8")
