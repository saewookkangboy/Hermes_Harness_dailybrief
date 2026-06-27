#!/usr/bin/env python3
"""CLI helper for newsletter-send.sh."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))

from lib.newsletter_esp import execute_send  # noqa: E402

stamp = sys.argv[1]
live = sys.argv[2] == "1"
to = sys.argv[3] if len(sys.argv) > 3 else ""
approved = os.environ.get("HERMES_ESP_APPROVED") == "1"
result = execute_send(stamp, live=live, to=to, approved=approved)
print(json.dumps(result, ensure_ascii=False, indent=2))
