#!/usr/bin/env bash
# Daily Content Triage Loop (L1) — 결정적, report-only
#
# 통합: Morning Pack · Quality Audit · Runtime Health
#       (+ 월요일: Competitive Watch · Agents Eval A–D 요약)
#
# Usage:
#   ./cron-daily-content-triage.sh
#   HERMES_TRIAGE_SKIP_AGENTS_EVAL=1 ./cron-daily-content-triage.sh
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
SESSION="${TELEGRAM_CHAT_ID:-cron-daily-triage}"
DOW="$(date +%u)"  # 1=Mon … 7=Sun

LOG="$WORKDIR/content/logs/${STAMP}_daily-triage.md"
RUNS="$WORKDIR/.harness/content-loop-runs.jsonl"
mkdir -p "$(dirname "$LOG")" "$(dirname "$RUNS")"

run_py() {
  if [[ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]]; then
    "$HOME/.hermes/hermes-agent/venv/bin/python" "$@"
  else
    python3 "$@"
  fi
}

section_morning() {
  echo "## 1. Morning Pack"
  echo ""
  "$DIR/hermes-agent.sh" morning --date "$STAMP" --session "$SESSION" 2>&1 || echo "⚠️ Morning pack 실패"
}

section_audit() {
  echo ""
  echo "## 2. Quality Audit"
  echo ""
  local out rc=0
  out=$("$DIR/run-quality-audit.sh" "$STAMP" 2>&1) || rc=$?
  echo "$out"
  if [[ "$rc" -ne 0 ]]; then
    echo ""
    echo "_Audit exit $rc — L1 triage는 리포트만, 자동 수정 없음_"
  fi
  return 0
}

section_health() {
  echo ""
  echo "## 3. Runtime Health"
  echo ""
  local issues
  issues=$(run_py -c "
import sys
sys.path.insert(0, '${DIR}')
from lib.runtime_health import run_runtime_checks
issues = run_runtime_checks('${STAMP}')
print(chr(10).join(issues) if issues else '✅ runtime OK')
" 2>/dev/null || echo "⚠️ health check 오류")
  echo "$issues"
}

section_watch() {
  [[ "$DOW" == "1" ]] || return 0
  echo ""
  echo "## 4. Competitive Watch (월)"
  echo ""
  run_py -c "
import sys
sys.path.insert(0, '${DIR}')
from lib.competitive_watch import run_competitive_watch, format_watch_summary
r = run_competitive_watch(write_report=True)
print(format_watch_summary(r))
" 2>&1 || echo "⚠️ competitive watch 실패"
}

section_agents_eval() {
  [[ "$DOW" == "1" ]] || return 0
  [[ "${HERMES_TRIAGE_SKIP_AGENTS_EVAL:-0}" == "1" ]] && return 0
  echo ""
  echo "## 5. Agents Eval A–D (월)"
  echo ""
  local out rc=0
  out=$("$DIR/agents-eval.sh" "$STAMP" 2>&1) || rc=$?
  echo "$out"
  if [[ "$rc" -ne 0 ]]; then
    echo ""
    echo "_Agents eval exit $rc — L1 triage는 리포트만_"
  fi
  return 0
}

append_run_log() {
  local status="$1"
  local ts
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf '{"ts":"%s","loop":"daily-content-triage","stamp":"%s","level":"L1","status":"%s","report":"content/logs/%s_daily-triage.md"}\n' \
    "$ts" "$STAMP" "$status" "$STAMP" >>"$RUNS"
}

# --- assemble report ---
{
  echo "# Daily Content Triage · ${STAMP}"
  echo ""
  echo "_Loop: daily-content-triage · Level L1 (report-only) · $(date '+%Y-%m-%d %H:%M %Z')_"
  echo ""
  section_morning
  section_audit
  section_health
  section_watch
  section_agents_eval
  echo ""
  echo "---"
  echo ""
  echo "📋 \`content/logs/${STAMP}_daily-triage.md\`"
} | tee "$LOG"

# Telegram/Slack digest (cron deliver + explicit notify)
SUMMARY=$(head -40 "$LOG")
if [[ -x "$DIR/lib/commander_notify.sh" ]]; then
  bash "$DIR/lib/commander_notify.sh" notify "$SUMMARY"
fi

append_run_log "OK"
echo ""
echo "saved: $LOG"
