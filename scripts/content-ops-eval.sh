#!/usr/bin/env bash
# Phase B Agent eval — HITL Scheduler · Pipeline Supervisor
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Content Ops Agents Eval (Phase B) — $STAMP ==="

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.publish_scheduler import schedule_publish, list_schedules, cancel_schedule, _parse_at
from datetime import datetime
from zoneinfo import ZoneInfo
_parse_at('+5m')
" 2>/dev/null && record PASS "scheduler_module" || record FAIL "scheduler_module"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.pipeline_supervisor import run_supervised_pipeline, SupervisorReport
" 2>/dev/null && record PASS "supervisor_module" || record FAIL "supervisor_module"

[[ -x "$DIR/run-supervised-pipeline.sh" ]] && record PASS "supervisor_script" || record FAIL "supervisor_script"
[[ -x "$DIR/cron-publish-schedule.sh" ]] && record PASS "schedule_cron" || record FAIL "schedule_cron"
# Hermes cron은 ~/.hermes/scripts + cwd=scripts — lib 경로 회귀 방지
( cd "$HOME/.hermes/scripts" && bash cron-publish-schedule.sh >/dev/null 2>&1 ) \
  && record PASS "cron_publish_hermes_scripts_cwd" || record FAIL "cron_publish_hermes_cwd"

grep -q "schedule:" "$WORKDIR/config/agent-commands.yaml" && record PASS "yaml_schedule" || record FAIL "yaml_schedule"
grep -q "supervised:" "$WORKDIR/config/agent-commands.yaml" && record PASS "yaml_supervised" || record FAIL "yaml_supervised"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.publish_scheduler import schedule_publish, cancel_schedule
s = schedule_publish('$STAMP', ['linkedin'], '+10m', note='eval')
cancel_schedule(s['id'])
" 2>/dev/null && record PASS "scheduler_e2e" || record FAIL "scheduler_e2e"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.pipeline_supervisor import run_supervised_pipeline
r = run_supervised_pipeline('$STAMP', skip_newsletter=True, skip_notion=True, skip_audit=True)
assert r.stages
" 2>/dev/null && record PASS "supervisor_e2e_dry" || record FAIL "supervisor_e2e_dry"

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
[[ "$FAIL" -eq 0 ]]
