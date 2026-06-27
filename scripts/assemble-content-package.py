#!/usr/bin/env python3
"""Assemble blog/instagram/linkedin + Notion packages from research brief."""
from __future__ import annotations

import sys
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
sys.path.insert(0, str(WORKDIR / "scripts"))

from lib.brief_gate import assert_brief_ready_for_content
from lib.common import slugify, studio_today  # noqa: E402
from lib.content_quality import (  # noqa: E402
    build_blog_html,
    build_instagram_md,
    build_linkedin_md,
    build_notion_packages,
    parse_brief,
)
from lib.humanize_korean import humanize  # noqa: E402
from lib.wiki_concepts import inject_wiki_blurbs  # noqa: E402


def read_brief(stamp: str) -> tuple[Path, str]:
    path = WORKDIR / "content" / "research" / f"{stamp}_brief.md"
    if not path.exists():
        raise FileNotFoundError(
            f"{stamp} 날짜 리서치 브리프가 없습니다: {path}\n"
            "먼저 실행: scripts/run-research-brief.sh 또는 telegram-pipeline.sh research"
        )
    return path, path.read_text(encoding="utf-8")


def main() -> int:
    stamp = sys.argv[1] if len(sys.argv) > 1 else studio_today()
    assert_brief_ready_for_content(stamp)
    brief_path, text = read_brief(stamp)
    summary, insights = parse_brief(text)
    summary = humanize(summary, genre="blog").text

    blog_dir = WORKDIR / "content/blog"
    ig_dir = WORKDIR / "content/instagram"
    li_dir = WORKDIR / "content/linkedin"
    pkg_dir = WORKDIR / "content/packages"
    for d in (blog_dir, ig_dir, li_dir, pkg_dir):
        d.mkdir(parents=True, exist_ok=True)

    slug = slugify(insights[0].korean_title if insights else "weekly")
    blog_html = blog_dir / f"{stamp}_blog_{slug}.html"
    ig_path = ig_dir / f"{stamp}_instagram_{slug}.md"
    li_path = li_dir / f"{stamp}_linkedin_{slug}.md"

    wiki_blurbs = inject_wiki_blurbs(insights)
    blog_html.write_text(build_blog_html(stamp, summary, insights, wiki_blurbs=wiki_blurbs), encoding="utf-8")
    ig_path.write_text(build_instagram_md(stamp, summary, insights, wiki_blurbs=wiki_blurbs), encoding="utf-8")
    li_path.write_text(build_linkedin_md(stamp, summary, insights, wiki_blurbs=wiki_blurbs), encoding="utf-8")

    notion_paths = build_notion_packages(stamp, text, summary, insights, pkg_dir)

    print(blog_html)
    print(ig_path)
    print(li_path)
    for p in notion_paths.values():
        print(p)
    print(f"# brief: {brief_path}", file=sys.stderr)
    print(f"# insights: {len(insights)}", file=sys.stderr)
    print(f"# blog chars: {len(notion_paths['blog'].read_text(encoding='utf-8'))}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
