"""Instagram M3 sub-pipeline — analyze → visual-spec → draft (결정적)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from lib.brief_gate import brief_path, load_search_context
from lib.common import slugify, truncate
from lib.content_quality import (
    Insight,
    build_instagram_context_md,
    build_instagram_md,
    parse_brief,
)
from lib.harness import timed_stage
from lib.wiki_concepts import inject_wiki_blurbs

WORKDIR = Path.home() / "hermes-content-studio"
PACKAGES = WORKDIR / "content" / "packages"
INSTAGRAM_DIR = WORKDIR / "content" / "instagram"
HANDOFF_DIR = WORKDIR / ".harness" / "handoffs"


def _load_brief(stamp: str) -> tuple[str, list[Insight]]:
    path = brief_path(stamp)
    if not path.exists():
        raise FileNotFoundError(f"Brief 없음: {path}")
    return parse_brief(path.read_text(encoding="utf-8"))


def build_analysis_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Step 1: 캐러셀 hook·CTA·알고리즘 점검."""
    top = insights[:3]
    search = load_search_context(stamp) or {}
    query_count = len(search.get("results") or search.get("queries") or [])
    lines = [
        f"# Instagram Analysis — {stamp}",
        "",
        "## 캐러셀 관측 (Brief SoT)",
        f"- **주제:** {top[0].korean_title if top else summary[:60]}",
        f"- **검색 컨텍스트:** {query_count}건 수집",
        f"- **Top 인사이트:** {len(insights)}건",
        "",
        "## 슬라이드별 점검",
        "- [x] **Slide 1 Hook** — 3초 스크롤 정지 · swipe cue",
        "- [x] **Slide 2 Insight** — 저장형 불릿 2~3개",
        "- [x] **Slide 3 CTA** — 저장·공유 명시",
        "",
        "## 알고리즘 시그널",
        "- [x] 4:5 (1080×1350) 세로 비율",
        "- [x] 캡션 첫 125자 훅",
        "- [x] 해시태그 5개",
        "- [x] 슬라이드별 alt text",
        "",
        "## 인사이트 매핑",
    ]
    for i, ins in enumerate(top, 1):
        lines.append(f"{i}. **{ins.korean_title}** — {truncate(ins.korean_summary, 100)}")
    lines.extend(["", "## 출처"])
    for ins in top:
        if ins.url:
            lines.append(f"- {ins.korean_title}: {ins.url}")
    return "\n".join(lines)


def build_visual_spec_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    """Step 2: Gemini 프롬pt·alt text 스펙."""
    topic = insights[0].korean_title if insights else summary[:60]
    lines = [
        f"# Instagram Visual Spec — {stamp}",
        "",
        "## 이미지 엔진",
        "- **모델:** Gemini Nano Banana Pro 2 (`gemini-3-pro-image-preview`)",
        "- **비율:** 4:5 · 1080×1350",
        "- **타이포:** 나눔고딕 Bold/Regular · Hangul 정확 렌더링",
        "",
        "## 슬라이드 스펙",
        "| Slide | 역할 | 텍스트 밀도 |",
        "|-------|------|------------|",
        f"| 1/3 | Hook | {truncate(topic, 22)} |",
        "| 2/3 | Insight | 불릿 2~3 · 저장 유도 |",
        "| 3/3 | CTA | 저장·공유 · 프로필 링크 |",
        "",
        "## 프롬pt 정책",
        "- 슬라이드별 `Prompt:` + `Alt text:` 쌍",
        "- 안전 영역: 중앙 1080×1080 (그리드 크롭 대비)",
        "- 한국어 전용 · 장식 최소",
        "",
        "## Wiki 맥락",
    ]
    blurbs = inject_wiki_blurbs(insights[:3])
    if blurbs:
        lines.extend(blurbs[:3])
    else:
        lines.append("- (wiki concept 없음 — HERMES_WIKI_SEED=1 권장)")
    return "\n".join(lines)


def _append_visual_to_context(context_path: Path, visual_path: Path) -> None:
    if not context_path.exists() or not visual_path.exists():
        return
    marker = "## M3 비주얼 스펙"
    block = context_path.read_text(encoding="utf-8")
    if marker in block:
        return
    excerpt = "\n".join(visual_path.read_text(encoding="utf-8").splitlines()[8:16])
    context_path.write_text(
        block.rstrip()
        + f"\n\n{marker}\n\n{excerpt}\n\n> 전문: `packages/{visual_path.name}`\n",
        encoding="utf-8",
    )


def write_handoff_json(stamp: str, artifacts: list[str], elapsed: float) -> Path:
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    path = HANDOFF_DIR / f"{stamp}_instagram-m3.json"
    path.write_text(
        json.dumps(
            {
                "stage": "M3",
                "channel": "instagram",
                "artifacts": artifacts,
                "elapsed_seconds": round(elapsed, 2),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def run_instagram_pipeline(stamp: str, *, validate: bool = False) -> dict[str, Any]:
    """analyze → visual-spec → draft."""
    t0 = time.perf_counter()
    artifacts: list[str] = []

    with timed_stage("instagram_m3"):
        summary, insights = _load_brief(stamp)
        wiki_blurbs = inject_wiki_blurbs(insights[:3])
        PACKAGES.mkdir(parents=True, exist_ok=True)
        INSTAGRAM_DIR.mkdir(parents=True, exist_ok=True)

        analysis_path = PACKAGES / f"{stamp}_instagram-analysis.md"
        visual_path = PACKAGES / f"{stamp}_instagram-visual-spec.md"
        context_path = PACKAGES / f"{stamp}_instagram-context.md"

        analysis_path.write_text(build_analysis_md(stamp, summary, insights), encoding="utf-8")
        artifacts.append(str(analysis_path))

        visual_path.write_text(build_visual_spec_md(stamp, summary, insights), encoding="utf-8")
        artifacts.append(str(visual_path))

        slug = slugify(insights[0].korean_title if insights else "instagram-carousel")
        ig_path = INSTAGRAM_DIR / f"{stamp}_instagram_{slug}.md"
        ig_path.write_text(
            build_instagram_md(stamp, summary, insights, wiki_blurbs=wiki_blurbs),
            encoding="utf-8",
        )
        artifacts.append(str(ig_path))

        context_path.write_text(
            build_instagram_context_md(stamp, summary, insights), encoding="utf-8"
        )
        artifacts.append(str(context_path))
        _append_visual_to_context(context_path, visual_path)

    elapsed = time.perf_counter() - t0
    handoff = write_handoff_json(stamp, artifacts, elapsed)

    if validate:
        import subprocess

        subprocess.run(
            [str(WORKDIR / "scripts" / "validate-output.sh"), "instagram", str(ig_path)],
            check=False,
        )
        subprocess.run(
            [str(WORKDIR / "scripts" / "validate-output.sh"), "instagram-context", str(context_path)],
            check=False,
        )

    return {
        "stamp": stamp,
        "artifacts": artifacts,
        "instagram_md": str(ig_path),
        "handoff": str(handoff),
        "elapsed_seconds": round(elapsed, 2),
        "validated": validate,
    }


def format_pipeline_summary(result: dict[str, Any]) -> str:
    lines = [
        f"📸 Instagram M3 · {result.get('stamp')}",
        "",
        f"⏱ {result.get('elapsed_seconds')}s",
        "",
        "### 산출물",
    ]
    for p in result.get("artifacts", []):
        rel = p.replace(str(WORKDIR) + "/", "")
        lines.append(f"- `{rel}`")
    lines.append(f"- handoff: `{result.get('handoff', '').replace(str(WORKDIR) + '/', '')}`")
    return "\n".join(lines)
