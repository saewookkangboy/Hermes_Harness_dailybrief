#!/usr/bin/env python3
"""Generate lecture slides (outline + HTML + PPTX) from topic and content text."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
sys.path.insert(0, str(WORKDIR / "scripts"))

from lib.claude_design_deck import paths_to_json  # noqa: E402
from lib.slide_generator import generate  # noqa: E402


def topic_from_brief(stamp: str) -> tuple[str, str]:
    brief_path = WORKDIR / "content" / "research" / f"{stamp}_brief.md"
    if not brief_path.exists():
        raise FileNotFoundError(f"Brief not found: {brief_path}")
    text = brief_path.read_text(encoding="utf-8")
    m = re.search(r"## 강의 아이디어 \(이번 주\)\n\n1\. \*\*(.+?)\*\*", text)
    topic = m.group(1) if m else "주간 트렌드 강의"
    content = text
    return topic, content


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate lecture slides")
    parser.add_argument("topic", nargs="?", help="Lecture title")
    parser.add_argument("--content", "-c", help="Lecture content text")
    parser.add_argument("--content-file", "-f", help="Path to content text file")
    parser.add_argument("--date", "-d", default=date.today().isoformat())
    parser.add_argument(
        "--preset",
        "-p",
        help="Design preset (content-studio, linear, notion, claude, stripe, vercel)",
    )
    parser.add_argument("--from-brief", metavar="STAMP", help="Use research brief")
    parser.add_argument(
        "--design-mode",
        choices=["basic", "claude-design"],
        default="basic",
        help="basic=template HTML; claude-design=base HTML for Hermes polish",
    )
    parser.add_argument("--json", action="store_true", help="Output paths as JSON")
    args = parser.parse_args()

    preset = args.preset
    if args.design_mode == "claude-design" and not preset:
        preset = "claude"

    if args.from_brief:
        topic, content = topic_from_brief(args.from_brief)
        stamp = args.from_brief
    else:
        if not args.topic:
            parser.error("topic required unless --from-brief")
        topic = args.topic
        stamp = args.date
        if args.content_file:
            content = Path(args.content_file).read_text(encoding="utf-8")
        elif args.content:
            content = args.content
        else:
            content = topic

    paths, preset_name = generate(topic, content, stamp, preset)

    if args.design_mode == "claude-design":
        base = paths["html"].with_name(paths["html"].stem + "_base.html")
        paths["html"].rename(base)
        paths["html_base"] = base
        paths["html"] = base.with_name(base.name.replace("_base.html", ".html"))

    if args.json:
        meta = paths_to_json(paths, topic, stamp, preset_name)
        meta["design_mode"] = args.design_mode
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    else:
        for path in paths.values():
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
