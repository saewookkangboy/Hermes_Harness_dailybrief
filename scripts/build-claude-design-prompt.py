#!/usr/bin/env python3
"""Print Hermes prompt for claude-design lecture deck."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
sys.path.insert(0, str(WORKDIR / "scripts"))

from lib.claude_design_deck import build_claude_design_prompt  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--stamp", required=True)
    p.add_argument("--outline", required=True)
    p.add_argument("--base-html", required=True)
    p.add_argument("--output-html", required=True)
    p.add_argument("--pptx", required=True)
    p.add_argument("--preset", default="claude")
    args = p.parse_args()
    print(
        build_claude_design_prompt(
            topic=args.topic,
            stamp=args.stamp,
            outline_path=Path(args.outline),
            base_html_path=Path(args.base_html),
            output_html_path=Path(args.output_html),
            pptx_path=Path(args.pptx),
            preset_name=args.preset,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
