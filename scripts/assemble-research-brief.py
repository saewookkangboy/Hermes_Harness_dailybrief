#!/usr/bin/env python3
"""Assemble daily AI·marketing research brief — Top 7 · 21년차 AX 페르소나."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from lib.brief_quality import (
    INSIGHT_LIMIT,
    PERSONA_INTRO,
    build_coverage_table,
    build_engineering_highlights,
    build_executive_summary,
    build_llm_platform_pulse,
    enrich_insight,
    is_usable_search_result,
    load_priority_query_order,
)

WORKDIR = Path.home() / "hermes-content-studio"
RESEARCH_DIR = WORKDIR / "content" / "research"

KOREA_QUERIES = {
    "digital marketing Korea AX transformation",
    "Korea AX AI transformation news 2026",
    "South Korea enterprise AI adoption 2026",
}


def load_context(stamp: str) -> dict:
    path = RESEARCH_DIR / f"_search_context_{stamp}.json"
    if not path.exists():
        raise FileNotFoundError(f"Search context not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def channel_for_query(query: str) -> str:
    q = query.lower()
    if "instagram" in q:
        return "instagram"
    if "linkedin" in q:
        return "linkedin"
    if "korea" in q or "south korea" in q:
        return "lecture"
    if "governance" in q or "literacy" in q or "training" in q:
        return "lecture"
    if "hermes" in q:
        return "lecture"
    if "aeo" in q or "seo" in q:
        return "blog"
    return "blog | linkedin"


def pick_insights(results: list[dict], limit: int = INSIGHT_LIMIT) -> list[dict]:
    """Top N — priority query 다양성 우선 (LLM 4사·거버넌스·하네스 포함)."""
    usable = [r for r in results if is_usable_search_result(r)]
    picked: list[dict] = []
    seen_urls: set[str] = set()
    used_queries: set[str] = set()

    def try_add(row: dict) -> bool:
        url = row.get("url", "")
        if not url or url in seen_urls:
            return False
        seen_urls.add(url)
        picked.append({**row, "channel": channel_for_query(row.get("query", ""))})
        used_queries.add(row.get("query", ""))
        return True

    for pq in load_priority_query_order():
        if len(picked) >= limit:
            break
        for row in usable:
            if row.get("query") == pq:
                try_add(row)
                break

    for row in usable:
        if len(picked) >= limit:
            break
        q = row.get("query", "")
        if q in used_queries:
            continue
        if try_add(row):
            used_queries.add(q)

    return picked[:limit]


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    return title[:120] if title else "제목 미확인"


def build_brief(ctx: dict) -> str:
    today = date.fromisoformat(ctx["date"])
    start = date.fromisoformat(ctx["period_start"])
    end = date.fromisoformat(ctx["period_end"])
    raw_insights = pick_insights(ctx.get("results", []))
    used_views: set[str] = set()
    enriched = [enrich_insight(item, used_views) for item in raw_insights]

    period_label = f"{today}" if start == end else f"{start}~{end}"
    themes = [i["korean_title"] for i in enriched[:3]]
    categories = list(dict.fromkeys(i["research_category"] for i in enriched))

    summary = build_executive_summary(period_label, enriched, categories, themes)

    lines = [
        "# 일일 AI·마케팅 리서치 브리프",
        f"**관측일:** {today}",
        f"**수집 기간:** {period_label} (일일 렌즈)",
        "**작성:** Hermes Content Studio (assemble-research-brief.py v2.1)",
        "",
        "## 페르소나",
        PERSONA_INTRO,
        "",
        "**전문 영역:** 브랜드 · 콘텐츠 · 퍼포먼스 · 그로스 · 마케팅 전략 · "
        "AI 리터러시 · AI 거버넌스 · 책임있는 AI · AX · AI Native",
        "",
        "## Executive Summary",
        summary,
        "",
        "## 리서치 프레임",
        "리서치 → 내용 요약 → Insight 도출 → 활용 방법 → 가이드·팁",
        "",
        build_coverage_table(enriched),
        build_llm_platform_pulse(enriched),
        f"## Top {INSIGHT_LIMIT} 인사이트",
    ]

    for i, item in enumerate(enriched, 1):
        title_en = clean_title(item["title"])
        lines.extend(
            [
                f"### {i}. {title_en}",
                f"- **한국어 제목:** {item['korean_title']}",
                f"- **리서치 영역:** {item['research_category']}",
                f"- **내용 요약:** {item['summary_ko']}",
                f"- **Insight 도출:** {item['insight_derivation']}",
                f"- **마케터 관점:** {item['marketer_view']}",
                f"- **활용 방법:** {item['utilization']}",
                f"- **가이드·팁:** {item['guides_tips']}",
                f"- **콘텐츠 소재:** {item['channel']}",
                f"- **출처:** {item['url']}",
                f"- **시장 영향:** {item['market_impact']}",
                f"- **한국 적용:** {item['korea_apply']}",
                f"- **기회:** {item['opportunity']}",
                f"- **신뢰도:** {item['trust']} — 2차 검증 권장(시의성·출처)",
                "",
            ]
        )

    lines.extend(
        [
            "## 심층 분석",
            "",
            "### 트렌드 교차점",
            f"Top {INSIGHT_LIMIT} 신호를 교차하면 에이전트 × AEO × AX × AI 거버넌스가 "
            "2026년 B2B·AI Native 조직 설계의 공통 축입니다.",
            "",
            "### AX·AI Native 도입 현황",
            "PoC·선언형 AI → use case·거버넌스·리터러시 기반 파일럿→확대. "
            "한국은 regulation·legacy·교육 수요가 두드러집니다.",
            "",
            build_engineering_highlights(enriched),
            "### SEO / AEO / GEO 키워드 맵",
            "| 유형 | 키워드 |",
            "|------|--------|",
            "| Primary | AI marketing, Agentic AI, AEO, AI governance |",
            "| Secondary | AX transformation, AI Native, harness engineering |",
            "| Long-tail | 2026 B2B AI literacy, responsible AI marketing |",
            "",
            "### 통합 콘텐츠 컨텍스트",
            f"아래 Top {INSIGHT_LIMIT} 인사이트를 단일 소스로 사용합니다. "
            "Blog · Instagram · LinkedIn은 `content/packages/` 참조.",
            "",
        ]
    )

    cal = [e["korean_title"] for e in enriched[:4]] + ["AI 리터러시·거버넌스"]
    while len(cal) < 4:
        cal.append("AX·에이전트")

    lines.extend(
        [
            "## 콘텐츠 캘린더 제안",
            "",
            "| 요일 | 채널 | 주제 | 근거 # |",
            "|------|------|------|--------|",
            f"| 매일 | research | 일일 AI·마케팅 브리프 | #1~#{INSIGHT_LIMIT} |",
            f"| 수 | blog | {cal[1][:28]} | #2 |",
            f"| 수 | instagram | {cal[0][:22]} 웹툰 | #1 |",
            f"| 수 | linkedin | {cal[2][:28]} | #3 |",
            f"| 금 | lecture | {cal[3][:28]} | #4,#5 |",
            "",
            "> **강의 자료**는 `/lecture` 명령으로 별도 생성.",
            "",
            "## 데이터 포인트",
            "",
            f"- 수집된 웹 검색: {ctx.get('count', 0)}건 (ddgs, {today})",
            f"- 인사이트: Top {len(enriched)} / 목표 {INSIGHT_LIMIT}",
            "- 커버리지: LLM 4사 · AX · 거버넌스 · 에이전트 · 하네스 · Repo",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    stamp = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    ctx = load_context(stamp)
    brief = build_brief(ctx)
    out = RESEARCH_DIR / f"{stamp}_brief.md"
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(brief, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
