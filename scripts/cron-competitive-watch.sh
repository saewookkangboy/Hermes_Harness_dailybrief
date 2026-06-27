#!/usr/bin/env bash
# Competitive Watch cron — Brief Graph 감시 digest (결정적)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"

run_py() {
  if [[ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]]; then
    "$HOME/.hermes/hermes-agent/venv/bin/python" "$@"
  else
    python3 "$@"
  fi
}

MSG=$(run_py -c "
import sys
sys.path.insert(0, '$DIR')
from lib.competitive_watch import run_competitive_watch, format_watch_summary
r = run_competitive_watch(write_report=True)
print(format_watch_summary(r))
print()
print(open(r['report_path'], encoding='utf-8').read())
")

LOG="$WORKDIR/content/logs/$(date +%Y-%m-%d)_competitive-watch-cron.md"
mkdir -p "$(dirname "$LOG")"
printf '%s\n' "$MSG" > "$LOG"

if [[ -x "$DIR/lib/commander_notify.sh" ]]; then
  SUMMARY=$(echo "$MSG" | head -12)
  bash "$DIR/lib/commander_notify.sh" notify "$SUMMARY"
fi

echo "$MSG"
echo ""
echo "saved: $LOG"
