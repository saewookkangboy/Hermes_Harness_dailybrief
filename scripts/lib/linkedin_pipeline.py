"""LinkedIn M3 sub-pipeline — analyze → strategy → draft (결정적)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from lib.brief_gate import brief_path, load_search_context
from lib.common import slugify, studio_today, truncate
from lib.content_quality import (
    Insight,
    build_linkedin_context_md,
    build_linkedin_md,
    parse_brief,
)
from lib.harness import timed_stage

WORKDIR = Path.home() / "hermes-content-studio"
PACKAGES = WORKDIR / "content" / "packages"
LINKEDIN_DIR = WORKDIR / "content" / "linkedin"
HANDOFF_DIR = WORKDIR / ".harness" / "handoffs"


def _load_brief(stamp: str) -> tuple[str, list[Insight]]:
    path = brief_path(stamp)
    if not path.exists():
        raise FileNotFoundError(f"Brief 없음: {path}")
    text = path.read_text(encoding="utf-8")
    return parse_brief(text)


def build_analysis_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Step 1: 피드·트렌드 분석."""
    top = insights[:3]
    search = load_search_context(stamp) or {}
    query_count = len(search.get("results") or search.get("queries") or [])
    lines = [
        f"# LinkedIn Analysis — {stamp}",
        "",
        "## 피드 관측 (Brief SoT)",
        f"- **주제:** {top[0].korean_title if top else summary[:60]}",
        f"- **검색 컨텍스트:** {query_count}건 수집",
        f"- **Top 인사이트:** {len(insights)}건",
        "",
        "## 트렌드 시그널",
    ]
    for i, ins in enumerate(top, 1):
        lines.append(f"{i}. **{ins.korean_title}** — {truncate(ins.korean_summary, 100)}")
    lines.extend(
        [
            "",
            "## 피드 리스크 체크",
            "- [x] hook 2줄 — see more 전 가치 제시",
            "- [x] 본문 URL 최소 — 첫 댓글 링크 전략",
            "- [x] 1300자 이내 · 문단 2줄",
            "- [x] 댓글 CTA (질문형)",
            "",
            "## 경쟁·맥락",
        ]
    )
    for ins in top:
        if ins.url:
            lines.append(f"- {ins.korean_title}: {ins.url}")
    return "\n".join(lines)


def build_strategy_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Step 2: 글 각도·훅 설계."""
    topic = insights[0].korean_title if insights else "2026 AI 마케팅"
    hook1 = f"한국 B2B, {truncate(topic, 35)} — ‘언제’보다 ‘어디서’ 손대느냐가 더 중요해요."
    hook2 = "에이전트 도구 고르기 전에 프롬프트·SOP·측정 3가지만 잡아도 속도가 달라져요."
    bullets = []
    for ins in insights[:3]:
        bullets.append(f"→ {truncate(ins.korean_title, 40)}: {truncate(ins.marketer_view or ins.korean_summary, 80)}")
    lines = [
        f"# LinkedIn Strategy — {stamp}",
        "",
        "## 각도 (Angle)",
        f"- **Primary:** {topic}",
        "- **포지션:** 21년차 현장형 마케터 · AX·AEO 실무 프레임",
        "- **대비:** 선언형 AI vs 실행 직전 가이드",
        "",
        "## Hook (2줄)",
        f"1. {hook1}",
        f"2. {hook2}",
        "",
        "## 불릿 우선순위",
        *bullets,
        "",
        "## CTA · 링크",
        "- **CTA:** 팀에서 AX/에이전트, 어디부터 시작하고 계세요? (댓글)",
        "- **링크:** 본문 URL 없음 → 첫 댓글에 블로그/Notion Permalink",
        "",
        "## 해시태그",
        "#AIMarketing #AEO #AgenticAI #B2BMarketing #AX",
    ]
    return "\n".join(lines)


def _append_strategy_to_context(context_path: Path, strategy_path: Path) -> None:
    if not context_path.exists() or not strategy_path.exists():
        return
    strategy = strategy_path.read_text(encoding="utf-8")
    excerpt = "\n".join(strategy.splitlines()[4:12])  # Angle + Hook 요약
    block = context_path.read_text(encoding="utf-8")
    marker = "## M3 전략 요약"
    if marker in block:
        return
    context_path.write_text(
        block.rstrip()
        + f"\n\n{marker}\n\n"
        + excerpt
        + "\n\n> 전문: `packages/{name}`\n".format(name=strategy_path.name),
        encoding="utf-8",
    )


def write_handoff_json(stamp: str, artifacts: list[str], elapsed: float) -> Path:
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    path = HANDOFF_DIR / f"{stamp}_linkedin-M3.json"
    payload = {
        "stage": "M3",
        "channel": "linkedin",
        "assumptions": ["Brief SoT 사용", "결정적 analyze→strategy→draft"],
        "inputs_used": {
            "brief_path": str(brief_path(stamp)),
            "search_context": str(WORKDIR / "content" / "research" / f"_search_context_{stamp}.json"),
        },
        "artifacts": {"paths": artifacts, "conditions_applied": ["feed_grammar", "hook_2lines"]},
        "quality_notes": ["validate-output.sh linkedin 권장"],
        "next_stage_ready": True,
        "handoff_payload": {"channel": "linkedin", "stamp": stamp},
        "elapsed_seconds": round(elapsed, 2),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_linkedin_pipeline(stamp: str | None = None, *, validate: bool = False) -> dict[str, Any]:
    """analyze → strategy → draft 전체 실행."""
    stamp = stamp or studio_today()
    t0 = time.perf_counter()
    artifacts: list[str] = []

    with timed_stage("linkedin_m3"):
        summary, insights = _load_brief(stamp)
        analysis_path = PACKAGES / f"{stamp}_linkedin-analysis.md"
        strategy_path = PACKAGES / f"{stamp}_linkedin-strategy.md"
        context_path = PACKAGES / f"{stamp}_linkedin-context.md"

        analysis_path.write_text(build_analysis_md(stamp, summary, insights), encoding="utf-8")
        artifacts.append(str(analysis_path))

        strategy_path.write_text(build_strategy_md(stamp, summary, insights), encoding="utf-8")
        artifacts.append(str(strategy_path))

        slug = slugify(insights[0].korean_title if insights else "linkedin-post")
        li_path = LINKEDIN_DIR / f"{stamp}_linkedin_{slug}.md"
        LINKEDIN_DIR.mkdir(parents=True, exist_ok=True)
        li_path.write_text(build_linkedin_md(stamp, summary, insights), encoding="utf-8")
        artifacts.append(str(li_path))

        PACKAGES.mkdir(parents=True, exist_ok=True)
        context_path.write_text(
            build_linkedin_context_md(stamp, summary, insights), encoding="utf-8"
        )
        artifacts.append(str(context_path))
        _append_strategy_to_context(context_path, strategy_path)

    elapsed = time.perf_counter() - t0
    handoff_path = write_handoff_json(stamp, artifacts, elapsed)

    result: dict[str, Any] = {
        "stamp": stamp,
        "artifacts": artifacts,
        "handoff": str(handoff_path),
        "elapsed_seconds": round(elapsed, 2),
    }
    if validate:
        import subprocess

        subprocess.run(
            ["scripts/validate-output.sh", "linkedin", str(li_path)],
            cwd=str(WORKDIR),
            check=False,
        )
    return result


def format_pipeline_summary(result: dict[str, Any]) -> str:
    lines = [
        f"💼 LinkedIn M3 Pipeline · {result['stamp']}",
        "",
        f"⏱ {result['elapsed_seconds']}s",
        "",
        "### 산출물",
    ]
    for p in result.get("artifacts", []):
        rel = p.replace(str(WORKDIR) + "/", "")
        lines.append(f"- `{rel}`")
    lines.append(f"- handoff: `{result.get('handoff', '').replace(str(WORKDIR) + '/', '')}`")
    return "\n".join(lines)
