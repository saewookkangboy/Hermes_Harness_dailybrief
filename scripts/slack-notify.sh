#!/usr/bin/env bash
# Send Slack notification via Bot API (chat.postMessage)
# Usage:
#   slack-notify.sh CHANNEL_ID "message"
#   echo "msg" | slack-notify.sh CHANNEL_ID --stdin
set -euo pipefail

CHANNEL="${1:?channel id}"
shift
DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

run_python() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

if [[ "${1:-}" == "--stdin" ]]; then
  run_python "$DIR/slack-notify.py" "$CHANNEL" --stdin
elif [[ $# -ge 3 && "$1" == "--progress" ]]; then
  run_python "$DIR/slack-notify.py" "$CHANNEL" "${2} ${3} ${4}"
else
  MSG="${*:-}"
  run_python "$DIR/slack-notify.py" "$CHANNEL" "$MSG"
fi
