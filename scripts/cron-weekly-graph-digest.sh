#!/usr/bin/env bash
# 주간 Brief Graph digest → Telegram/Slack deliver (결정적, LLM 없음)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
DAYS="${GRAPH_DAYS:-14}"
# shellcheck source=lib/cron_bootstrap.sh
source "$WORKDIR/scripts/lib/cron_bootstrap.sh"

MSG=$(cron_run_py -c "
import sys
sys.path.insert(0, '${SCRIPTS_DIR}')
from lib.brief_graph import format_weekly_digest, save_brief_graph
save_brief_graph($DAYS)
print(format_weekly_digest($DAYS))
")

LOG="$WORKDIR/content/logs/$(date +%Y-%m-%d)_weekly-graph-digest.md"
mkdir -p "$(dirname "$LOG")"
printf '%s\n' "$MSG" > "$LOG"

if [[ -x "$SCRIPTS_DIR/lib/commander_notify.sh" ]]; then
  bash "$SCRIPTS_DIR/lib/commander_notify.sh" notify "$MSG"
fi

echo "$MSG"
echo ""
echo "saved: $LOG"
