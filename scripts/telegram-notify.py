#!/usr/bin/env python3
"""CLI for Telegram notifications."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
sys.path.insert(0, str(WORKDIR / "scripts"))

from lib.telegram_notify import format_notion_summary, format_progress, send_message  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("chat_id")
    parser.add_argument("message", nargs="?", default="")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--progress", nargs=3, metavar=("STEP", "TOTAL", "LABEL"))
    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read()
    elif args.progress:
        text = format_progress(int(args.progress[0]), int(args.progress[1]), args.progress[2])
    else:
        text = args.message

    ok = send_message(args.chat_id, text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
