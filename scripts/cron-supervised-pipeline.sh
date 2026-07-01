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
# Env (defaults from config/content-quality.yaml supervised.cron_defaults; override):
#   HERMES_CRON_SKIP_NEWSLETTER   # 1=M2b 제외
#   HERMES_CRON_SKIP_NOTION       # 1=M5 제외
#   HERMES_CRON_SKIP_AUDIT        # 1=Audit 제외
#   HERMES_CRON_HUMANIZE          # 1=M2 후 결정적 humanize polish
#   HERMES_SUPERVISED_STAGING=1   # staging.*_blocking (naturalness FAIL 테스트)
#   HERMES_NATURALNESS_BLOCKING=1 # 프로덕션 yaml 없이 naturalness FAIL 강제
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

_py_cron_default() {
  local field="$1"
  python3 -c "
import sys
sys.path.insert(0, '${DIR}')
from lib.content_quality_config import supervised_cron_defaults
d = supervised_cron_defaults()
field = sys.argv[1]
if field == 'humanize':
    print('1' if d['humanize'] else '0')
elif field == 'skip_newsletter':
    print('1' if d['skip_newsletter'] else '0')
elif field == 'skip_notion':
    print('1' if d['skip_notion'] else '0')
elif field == 'skip_audit':
    print('1' if d['skip_audit'] else '0')
else:
    raise SystemExit(f'unknown field: {field}')
" "$field"
}

SKIP_NEWSLETTER="${HERMES_CRON_SKIP_NEWSLETTER:-$(_py_cron_default skip_newsletter)}"
SKIP_NOTION="${HERMES_CRON_SKIP_NOTION:-$(_py_cron_default skip_notion)}"
SKIP_AUDIT="${HERMES_CRON_SKIP_AUDIT:-$(_py_cron_default skip_audit)}"
CRON_HUMANIZE="${HERMES_CRON_HUMANIZE:-$(_py_cron_default humanize)}"

LOG="$WORKDIR/content/logs/${STAMP}_supervised-pipeline.md"
HANDOFF="$WORKDIR/.harness/handoffs/${STAMP}_supervised-pipeline.json"
RUNS="$WORKDIR/.harness/content-loop-runs.jsonl"
mkdir -p "$(dirname "$LOG")" "$(dirname "$RUNS")" "$(dirname "$HANDOFF")"

if [[ "${HERMES_CRON_SUPERVISED_DRY_RUN:-0}" == "1" ]]; then
  echo "Supervised Pipeline (dry-run) · $STAMP"
  echo "  SKIP_NEWSLETTER=$SKIP_NEWSLETTER"
  echo "  SKIP_NOTION_ARCHIVE=$SKIP_NOTION"
  echo "  SKIP_AUDIT=$SKIP_AUDIT"
  echo "  HERMES_CRON_HUMANIZE=$CRON_HUMANIZE"
  echo "  log: content/logs/${STAMP}_supervised-pipeline.md"
  exit 0
fi

append_run_log() {
  local status="$1" blocked="${2:-}"
  local ts voice_st nat_st
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  voice_st=""
  nat_st=""
  if [[ -f "$HANDOFF" ]]; then
    read -r voice_st nat_st < <(python3 -c "
import json
from pathlib import Path
p = Path('$HANDOFF')
if not p.exists():
    print(' ', ' ')
    raise SystemExit
d = json.loads(p.read_text(encoding='utf-8'))
by_id = {s.get('id'): s.get('status', '') for s in d.get('stages', [])}
print(by_id.get('VOICE', ''), by_id.get('NATURALNESS', ''))
" 2>/dev/null || echo " ")
  fi
  printf '{"ts":"%s","loop":"supervised-pipeline","stamp":"%s","level":"L2","status":"%s","blocked_at":"%s","skip_newsletter":"%s","humanize":"%s","voice":"%s","naturalness":"%s","report":"content/logs/%s_supervised-pipeline.md"}\n' \
    "$ts" "$STAMP" "$status" "$blocked" "$SKIP_NEWSLETTER" "$CRON_HUMANIZE" "${voice_st:-}" "${nat_st:-}" "$STAMP" >>"$RUNS"
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
export HERMES_HUMANIZE="$CRON_HUMANIZE"
[[ "${HERMES_SUPERVISED_STAGING:-0}" == "1" ]] && export HERMES_SUPERVISED_STAGING=1

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
  echo "| HERMES_CRON_HUMANIZE | ${CRON_HUMANIZE} |"
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
