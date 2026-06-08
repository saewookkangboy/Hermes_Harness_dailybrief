#!/usr/bin/env python3
"""Assemble B2B newsletter from research brief (Brief SoT)."""
from __future__ import annotations

import sys
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
sys.path.insert(0, str(WORKDIR / "scripts"))

from lib.brief_gate import assert_brief_ready_for_content, brief_path  # noqa: E402
from lib.common import studio_today  # noqa: E402
from lib.newsletter_quality import assemble_newsletter  # noqa: E402


def main() -> int:
    stamp = sys.argv[1] if len(sys.argv) > 1 else studio_today()
    assert_brief_ready_for_content(stamp)
    path = brief_path(stamp)
    text = path.read_text(encoding="utf-8")
    nl_path, ctx_path, html_path, paste_path = assemble_newsletter(stamp, text)
    print(nl_path)
    print(ctx_path)
    print(html_path)
    print(paste_path)
    print(f"# brief: {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
