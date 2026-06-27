#!/usr/bin/env bash
# Supervised Pipeline Loop (L2) — M1→M2→(M2b)→Audit→M5 (결정적)
#
# triage(09:30) 이후 평일 자동 실행 · 실패 시 blocked_at + handoff JSON
#
# Usage:
#   ./cron-supervised-pipeline.sh
#   HERMES_CRON_SKIP_NEWSLETTER=0 ./cron-supervised-pipeline.sh
#   HERMES_CRON_SUPERVISED_DRY_RUN=1 ./cron-supervised-pipeline.sh
#
# Env (defaults):
#   HERMES_CRON_SKIP_NEWSLETTER=1   # rollout: M2b 제외 (2주 후 0 권장)
#   HERMES_CRON_SKIP_NOTION=0       # M5 Notion sync ON
#   HERMES_CRON_SKIP_AUDIT=0        # Quality Audit ON
#
# hermes cron --no-agent · stdout → Telegram deliver
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"

DATE="$(studio_commander_date)"
STAMP="$DATE"
export DATE

SKIP_NEWSLETTER="${HERMES_CRON_SKIP_NEWSLETTER:-1}"
SKIP_NOTION="${HERMES_CRON_SKIP_NOTION:-0}"
SKIP_AUDIT="${HERMES_CRON_SKIP_AUDIT:-0}"

LOG="$WORKDIR/content/logs/${STAMP}_supervised-pipeline.md"
HANDOFF="$WORKDIR/.harness/handoffs/${STAMP}_supervised-pipeline.json"
RUNS="$WORKDIR/.harness/content-loop-runs.jsonl"
mkdir -p "$(dirname "$LOG")" "$(dirname "$RUNS")" "$(dirname "$HANDOFF")"

if [[ "${HERMES_CRON_SUPERVISED_DRY_RUN:-0}" == "1" ]]; then
  echo "Supervised Pipeline (dry-run) · $STAMP"
  echo "  SKIP_NEWSLETTER=$SKIP_NEWSLETTER"
  echo "  SKIP_NOTION_ARCHIVE=$SKIP_NOTION"
  echo "  SKIP_AUDIT=$SKIP_AUDIT"
  echo "  log: content/logs/${STAMP}_supervised-pipeline.md"
  exit 0
fi

append_run_log() {
  local status="$1" blocked="${2:-}"
  local ts
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf '{"ts":"%s","loop":"supervised-pipeline","stamp":"%s","level":"L2","status":"%s","blocked_at":"%s","skip_newsletter":"%s","report":"content/logs/%s_supervised-pipeline.md"}\n' \
    "$ts" "$STAMP" "$status" "$blocked" "$SKIP_NEWSLETTER" "$STAMP" >>"$RUNS"
}

notify_report() {
  local msg="$1"
  if [[ -x "$DIR/lib/commander_notify.sh" ]]; then
    bash "$DIR/lib/commander_notify.sh" notify "$msg"
  fi
}

# --- run supervised pipeline ---
export SKIP_INIT=1
export SKIP_NEWSLETTER="$SKIP_NEWSLETTER"
export SKIP_NOTION_ARCHIVE="$SKIP_NOTION"
export SKIP_AUDIT="$SKIP_AUDIT"

PIPE_OUT=""
PIPE_RC=0
PIPE_OUT=$("$DIR/run-supervised-pipeline.sh" "$STAMP" 2>&1) || PIPE_RC=$?

{
  echo "# Supervised Pipeline Cron · ${STAMP}"
  echo ""
  echo "_Loop: supervised-pipeline · Level L2 · $(date '+%Y-%m-%d %H:%M %Z')_"
  echo ""
  echo "| Option | Value |"
  echo "|--------|-------|"
  echo "| SKIP_NEWSLETTER | ${SKIP_NEWSLETTER} |"
  echo "| SKIP_NOTION_ARCHIVE | ${SKIP_NOTION} |"
  echo "| SKIP_AUDIT | ${SKIP_AUDIT} |"
  echo ""
  echo "$PIPE_OUT"
} >"$LOG"

# blocked_at from handoff JSON if present
BLOCKED=""
if [[ -f "$HANDOFF" ]]; then
  BLOCKED=$(python3 -c "
import json
from pathlib import Path
p = Path('$HANDOFF')
d = json.loads(p.read_text(encoding='utf-8'))
print(d.get('blocked_at') or '')
" 2>/dev/null || true)
fi

if [[ "$PIPE_RC" -eq 0 ]]; then
  append_run_log "OK" ""
  SUMMARY=$(head -25 "$LOG")
  notify_report "$SUMMARY"
  cat "$LOG"
  echo ""
  echo "saved: $LOG"
  exit 0
fi

append_run_log "FAIL" "${BLOCKED:-unknown}"
FAIL_MSG="❌ Supervised Pipeline · ${STAMP}"
[[ -n "$BLOCKED" ]] && FAIL_MSG="${FAIL_MSG}
blocked: **${BLOCKED}**"
FAIL_MSG="${FAIL_MSG}

$(head -20 "$LOG")"
notify_report "$FAIL_MSG"
cat "$LOG"
echo ""
echo "handoff: $HANDOFF"
echo "saved: $LOG"
exit "$PIPE_RC"
