#!/usr/bin/env bash
# Slack Bot scope 검증 — missing_scope 시 필요 scope 출력
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/slack_home.sh
source "$DIR/lib/slack_home.sh"
CH="$(studio_slack_home_channel)"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

run_py() { if [[ -x "$HERMES_PY" ]]; then "$HERMES_PY" "$@"; else python3 "$@"; fi; }

run_py - "$CH" <<'PY'
import json, sys, urllib.request
sys.path.insert(0, "/Users/chunghyo/hermes-content-studio/scripts")
from lib.slack_notify import get_bot_token

ch = sys.argv[1]
token = get_bot_token()
if not token:
    print("NO_TOKEN")
    sys.exit(1)

checks = [
    ("auth.test", "GET", "https://slack.com/api/auth.test", None),
    (
        "chat.postMessage",
        "POST",
        "https://slack.com/api/chat.postMessage",
        {"channel": ch, "text": "scope-check"},
    ),
    (
        "conversations.info",
        "GET",
        f"https://slack.com/api/conversations.info?channel={ch}",
        None,
    ),
]

missing = set()
for name, method, url, body in checks:
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
    ok = d.get("ok")
    err = d.get("error", "")
    needed = d.get("needed", "")
    print(f"{name}: {'OK' if ok else 'FAIL'} {err or ''} {('needed=' + needed) if needed else ''}")
    if not ok and needed:
        missing.update(s.strip() for s in needed.split(",") if s.strip())

if missing:
    print("")
    print("MISSING_SCOPES:", ",".join(sorted(missing)))
    print("")
    print("수정:")
    print("  1. https://api.slack.com/apps → OAuth & Permissions → Bot Token Scopes 추가")
    print("  2. Install App → Reinstall to Workspace")
    print("  3. Bot User OAuth Token (xoxb-) 재복사 → setup-slack.sh")
    sys.exit(2)

print("ALL_OK")
PY
