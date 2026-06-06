#!/usr/bin/env bash
# Send Telegram notification via Bot API
# Usage:
#   telegram-notify.sh CHAT_ID "message"
#   echo "msg" | telegram-notify.sh CHAT_ID --stdin
set -euo pipefail

CHAT="${1:?chat id}"
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
  run_python "$DIR/telegram-notify.py" "$CHAT" --stdin
elif [[ $# -ge 3 && "$1" == "--progress" ]]; then
  run_python "$DIR/telegram-notify.py" "$CHAT" --progress "$2" "$3" "$4"
else
  MSG="${*:-}"
  run_python "$DIR/telegram-notify.py" "$CHAT" "$MSG"
fi
