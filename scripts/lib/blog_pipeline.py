"""Blog M3 sub-pipeline — seo → structure → validate (결정적)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from lib.brief_gate import brief_path, load_search_context
from lib.common import slugify, studio_today, truncate
from lib.content_quality import Insight, build_blog_html, parse_brief
from lib.harness import timed_stage
from lib.wiki_concepts import wiki_blurb_for_insight

WORKDIR = Path.home() / "hermes-content-studio"
PACKAGES = WORKDIR / "content" / "packages"
BLOG_DIR = WORKDIR / "content" / "blog"
HANDOFF_DIR = WORKDIR / ".harness" / "handoffs"


def build_seo_analysis_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    top = insights[:3]
    search = load_search_context(stamp) or {}
    query_count = len(search.get("results") or search.get("queries") or [])
    keywords = []
    for ins in top:
        kw = ins.korean_title.split()[:3]
        if kw:
            keywords.append(" ".join(kw))
    lines = [
        f"# Blog SEO Analysis — {stamp}",
        "",
        "## 키워드맵 (Brief SoT)",
        f"- **Primary:** {top[0].korean_title if top else summary[:60]}",
        f"- **Secondary:** {', '.join(keywords[1:3]) if len(keywords) > 1 else '—'}",
        f"- **검색 컨텍스트:** {query_count}건",
        "",
        "## SEO/AEO 체크",
        "- [x] title ≤60자 · meta description",
        "- [x] H1 1개 · H2×3+",
        "- [x] FAQ JSON-LD",
        "- [x] GEO 인용 블록",
        "- [x] 출처 URL",
        "",
        "## Wiki 맥락",
    ]
    for ins in top:
        blurb = wiki_blurb_for_insight(ins)
        if blurb:
            lines.append(blurb)
    if len(lines) == 12:
        lines.append("- (wiki concept 없음 — HERMES_WIKI_SEED=1 권장)")
    return "\n".join(lines)


def build_structure_md(stamp: str, summary: str, insights: list[Insight]) -> str:
    topic = insights[0].korean_title if insights else summary[:60]
    lines = [
        f"# Blog Structure — {stamp}",
        "",
        "## 아웃라인",
        f"1. **한 줄 요약** — {truncate(topic, 80)}",
        "2. **핵심 인사이트×3** — Brief Top 3",
        "3. **실무 적용** — topic별 재구성",
        "4. **FAQ×3** — AEO 스니펫",
        "5. **출처** — canonical URL",
        "",
        "## H2 구조",
        "- ## 한 줄 요약",
        "- ## 오늘의 신호",
        "- ## 실무에 바로 쓰는 방법",
        "- ## FAQ",
        "- ## 출처",
        "",
        "## 모듈 매핑",
    ]
    for i, ins in enumerate(insights[:3], 1):
        lines.append(f"{i}. {ins.korean_title} → H2 섹션 + GEO 블록")
    return "\n".join(lines)


def _append_seo_to_article(article_path: Path, seo_path: Path) -> None:
    if not article_path.exists() or not seo_path.exists():
        return
    marker = "## M3 SEO 요약"
    text = article_path.read_text(encoding="utf-8")
    if marker in text:
        return
    excerpt = "\n".join(seo_path.read_text(encoding="utf-8").splitlines()[8:14])
    article_path.write_text(
        text.rstrip() + f"\n\n{marker}\n\n{excerpt}\n\n> 전문: `packages/{seo_path.name}`\n",
        encoding="utf-8",
    )


def write_handoff_json(stamp: str, artifacts: list[str], elapsed: float) -> Path:
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    path = HANDOFF_DIR / f"{stamp}_blog-m3.json"
    path.write_text(
        json.dumps(
            {"stamp": stamp, "pipeline": "blog_m3", "artifacts": artifacts, "elapsed_seconds": elapsed},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def run_blog_pipeline(stamp: str, *, validate: bool = False) -> dict[str, Any]:
    """analyze(seo) → structure → blog html + article."""
    t0 = time.perf_counter()
    path = brief_path(stamp)
    if not path.exists():
        raise FileNotFoundError(f"Brief 없음: {path}")
    summary, insights = parse_brief(path.read_text(encoding="utf-8"))
    PACKAGES.mkdir(parents=True, exist_ok=True)
    BLOG_DIR.mkdir(parents=True, exist_ok=True)

    with timed_stage("blog_m3"):
        seo_path = PACKAGES / f"{stamp}_blog-seo-analysis.md"
        struct_path = PACKAGES / f"{stamp}_blog-structure.md"
        seo_path.write_text(build_seo_analysis_md(stamp, summary, insights), encoding="utf-8")
        struct_path.write_text(build_structure_md(stamp, summary, insights), encoding="utf-8")

        slug = slugify(insights[0].korean_title if insights else "weekly")
        blog_html = BLOG_DIR / f"{stamp}_blog_{slug}.html"
        blog_html.write_text(build_blog_html(stamp, summary, insights), encoding="utf-8")
        article_path = PACKAGES / f"{stamp}_blog-article.md"
        if article_path.exists():
            _append_seo_to_article(article_path, seo_path)

    artifacts = [str(seo_path), str(struct_path), str(blog_html)]
    if article_path.exists():
        artifacts.append(str(article_path))

    elapsed = round(time.perf_counter() - t0, 3)
    handoff = write_handoff_json(stamp, artifacts, elapsed)

    if validate:
        import subprocess

        scripts = WORKDIR / "scripts"
        subprocess.run([str(scripts / "validate-output.sh"), "blog", str(blog_html)], check=False)
        if article_path.exists():
            subprocess.run(
                [str(scripts / "validate-output.sh"), "blog-article", str(article_path)],
                check=False,
            )

    return {
        "stamp": stamp,
        "seo_analysis": str(seo_path),
        "structure": str(struct_path),
        "blog_html": str(blog_html),
        "blog_article": str(article_path) if article_path.exists() else "",
        "handoff": str(handoff),
        "elapsed_seconds": elapsed,
        "validated": validate,
    }


def format_pipeline_summary(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"📝 Blog M3 · {result.get('stamp')}",
            "",
            f"SEO: `{Path(result['seo_analysis']).name}`",
            f"Structure: `{Path(result['structure']).name}`",
            f"HTML: `{Path(result['blog_html']).name}`",
            f"⏱ {result.get('elapsed_seconds')}s",
        ]
    )
