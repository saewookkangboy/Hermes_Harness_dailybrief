#!/usr/bin/env python3
"""CLI wrapper for lib.slack_notify."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.slack_notify import send_message  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: slack-notify.py CHANNEL_ID message", file=sys.stderr)
        return 1
    channel = sys.argv[1]
    if sys.argv[2] == "--stdin":
        text = sys.stdin.read()
    else:
        text = " ".join(sys.argv[2:])
    return 0 if send_message(channel, text) else 1


if __name__ == "__main__":
    raise SystemExit(main())
