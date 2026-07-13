#!/usr/bin/env bash
# Notion MCP OAuth 상태 점검 (exit 0=OK)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_PY="${HERMES_PY:-$HOME/.hermes/hermes-agent/venv/bin/python}"

if [[ -x "$HERMES_PY" ]]; then
  "$HERMES_PY" - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.notion_oauth import check_notion_oauth_status, format_oauth_alert
status = check_notion_oauth_status()
if not status.ok:
    print(format_oauth_alert(status))
    raise SystemExit(1)
print(status.detail)
if status.expires_in_hours is not None:
    print(f"만료까지 {status.expires_in_hours:.1f}h")
PY
else
  python3 - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.notion_oauth import check_notion_oauth_status, format_oauth_alert
status = check_notion_oauth_status()
if not status.ok:
    print(format_oauth_alert(status))
    raise SystemExit(1)
print(status.detail)
PY
fi
