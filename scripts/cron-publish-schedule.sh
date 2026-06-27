#!/usr/bin/env bash
# HITL Publish Scheduler cron — due 예약 → HITL 카드 전송 (결정적)
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

OUT=$(run_py -c "
import sys
sys.path.insert(0, '$DIR')
from lib.publish_scheduler import process_due_schedules
done = process_due_schedules(notify=True)
if not done:
    print('no due schedules')
else:
    for d in done:
        print('notified:', d.get('id'), d.get('stamp'))
")

LOG="$WORKDIR/content/logs/$(date +%Y-%m-%d)_publish-schedule-cron.md"
mkdir -p "$(dirname "$LOG")"
{
  echo "# Publish Schedule Cron — $(date '+%Y-%m-%d %H:%M')"
  echo ""
  echo "\`\`\`"
  echo "$OUT"
  echo "\`\`\`"
} >>"$LOG"

echo "$OUT"
