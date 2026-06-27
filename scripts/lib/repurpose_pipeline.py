"""Repurpose Agent — Brief SoT 인사이트 1건 → 채널별 재조립 (결정적)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from lib.brief_gate import brief_path
from lib.common import slugify, truncate
from lib.content_quality import (
    Insight,
    build_blog_html,
    build_instagram_context_md,
    build_instagram_md,
    build_linkedin_context_md,
    build_linkedin_md,
    parse_brief,
)
from lib.harness import timed_stage
from lib.newsletter_quality import build_newsletter_context_md, build_newsletter_md
from lib.wiki_concepts import inject_wiki_blurbs

WORKDIR = Path.home() / "hermes-content-studio"
PACKAGES = WORKDIR / "content" / "packages"
HANDOFF_DIR = WORKDIR / ".harness" / "handoffs"

VALID_CHANNELS = ("blog", "instagram", "linkedin", "newsletter")


def _select_insights(insights: list[Insight], index: int) -> list[Insight]:
    """1-based index → 해당 인사이트를 primary로 재정렬."""
    if not insights:
        return []
    idx = max(1, min(index, len(insights))) - 1
    primary = insights[idx]
    rest = [ins for i, ins in enumerate(insights) if i != idx]
    return [primary, *rest[:2]]


def _suffix(index: int) -> str:
    return f"i{index}"


def run_repurpose(
    stamp: str,
    channel: str,
    insight_index: int = 1,
    *,
    validate: bool = False,
) -> dict[str, Any]:
    """Brief Top N 중 1건을 primary로 채널 산출물 재생성."""
    channel = channel.lower()
    if channel not in VALID_CHANNELS:
        raise ValueError(f"채널: {' | '.join(VALID_CHANNELS)} (got {channel})")

    path = brief_path(stamp)
    if not path.exists():
        raise FileNotFoundError(f"Brief 없음: {path}")

    brief_text = path.read_text(encoding="utf-8")
    summary, all_insights = parse_brief(brief_text)
    if not all_insights:
        raise ValueError("Brief 인사이트 없음")

    insights = _select_insights(all_insights, insight_index)
    primary = insights[0]
    slug_base = slugify(primary.korean_title)
    slug = f"{slug_base}-{_suffix(insight_index)}"
    t0 = time.perf_counter()
    artifacts: list[str] = []

    with timed_stage(f"repurpose_{channel}"):
        if channel == "blog":
            out_dir = WORKDIR / "content" / "blog"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{stamp}_blog_{slug}.html"
            out_path.write_text(build_blog_html(stamp, summary, insights), encoding="utf-8")
            artifacts.append(str(out_path))

        elif channel == "instagram":
            wiki_blurbs = inject_wiki_blurbs(insights)
            ig_dir = WORKDIR / "content" / "instagram"
            ig_dir.mkdir(parents=True, exist_ok=True)
            ig_path = ig_dir / f"{stamp}_instagram_{slug}.md"
            ig_path.write_text(
                build_instagram_md(stamp, summary, insights, wiki_blurbs=wiki_blurbs),
                encoding="utf-8",
            )
            PACKAGES.mkdir(parents=True, exist_ok=True)
            ctx_path = PACKAGES / f"{stamp}_instagram-context_{_suffix(insight_index)}.md"
            ctx_path.write_text(
                build_instagram_context_md(stamp, summary, insights), encoding="utf-8"
            )
            artifacts.extend([str(ig_path), str(ctx_path)])

        elif channel == "linkedin":
            li_dir = WORKDIR / "content" / "linkedin"
            li_dir.mkdir(parents=True, exist_ok=True)
            li_path = li_dir / f"{stamp}_linkedin_{slug}.md"
            li_path.write_text(build_linkedin_md(stamp, summary, insights), encoding="utf-8")
            ctx_path = PACKAGES / f"{stamp}_linkedin-context_{_suffix(insight_index)}.md"
            PACKAGES.mkdir(parents=True, exist_ok=True)
            ctx_path.write_text(
                build_linkedin_context_md(stamp, summary, insights), encoding="utf-8"
            )
            artifacts.extend([str(li_path), str(ctx_path)])

        elif channel == "newsletter":
            nl_dir = WORKDIR / "content" / "newsletter"
            nl_dir.mkdir(parents=True, exist_ok=True)
            PACKAGES.mkdir(parents=True, exist_ok=True)
            nl_path = nl_dir / f"{stamp}_newsletter_{slug}.md"
            ctx_path = PACKAGES / f"{stamp}_newsletter-context_{_suffix(insight_index)}.md"
            nl_path.write_text(build_newsletter_md(stamp, summary, insights), encoding="utf-8")
            ctx_path.write_text(
                build_newsletter_context_md(stamp, summary, insights), encoding="utf-8"
            )
            artifacts.extend([str(nl_path), str(ctx_path)])

    elapsed = round(time.perf_counter() - t0, 3)
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    handoff_path = HANDOFF_DIR / f"{stamp}_repurpose-{channel}-{_suffix(insight_index)}.json"
    payload = {
        "stamp": stamp,
        "channel": channel,
        "insight_index": insight_index,
        "primary_title": primary.korean_title,
        "artifacts": artifacts,
        "elapsed_seconds": elapsed,
    }
    handoff_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if validate and artifacts:
        import subprocess

        vmap = {
            "blog": ("blog", artifacts[0]),
            "instagram": ("instagram", artifacts[0]),
            "linkedin": ("linkedin", artifacts[0]),
            "newsletter": ("newsletter", artifacts[0]),
        }
        vtype, vpath = vmap[channel]
        subprocess.run(
            [str(WORKDIR / "scripts" / "validate-output.sh"), vtype, vpath],
            check=False,
        )

    return {
        **payload,
        "handoff": str(handoff_path),
        "validated": validate,
    }


def format_repurpose_summary(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"♻️ Repurpose · {result.get('channel')} · insight #{result.get('insight_index')}",
            "",
            f"**Primary:** {truncate(result.get('primary_title', ''), 60)}",
            f"⏱ {result.get('elapsed_seconds')}s",
            "",
            "### 산출물",
            *[f"- `{Path(p).name}`" for p in result.get("artifacts", [])],
            f"- handoff: `{Path(result.get('handoff', '')).name}`",
        ]
    )
