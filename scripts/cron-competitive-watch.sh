#!/usr/bin/env bash
# Competitive Watch cron — Brief Graph 감시 digest (결정적)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
# shellcheck source=lib/cron_bootstrap.sh
source "$WORKDIR/scripts/lib/cron_bootstrap.sh"

MSG=$(cron_run_py -c "
import sys
sys.path.insert(0, '${SCRIPTS_DIR}')
from lib.competitive_watch import run_competitive_watch, format_watch_summary
r = run_competitive_watch(write_report=True)
print(format_watch_summary(r))
print()
print(open(r['report_path'], encoding='utf-8').read())
")

LOG="$WORKDIR/content/logs/$(date +%Y-%m-%d)_competitive-watch-cron.md"
mkdir -p "$(dirname "$LOG")"
printf '%s\n' "$MSG" > "$LOG"

if [[ -x "$SCRIPTS_DIR/lib/commander_notify.sh" ]]; then
  bash "$SCRIPTS_DIR/lib/commander_notify.sh" notify "$MSG"
fi

echo "$MSG"
echo ""
echo "saved: $LOG"
