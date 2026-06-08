#!/usr/bin/env bash
# Commander Phases 1–4 eval (morning cron · ask+graph · HITL · Slack parity)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="$(studio_today 2>/dev/null || date +%Y-%m-%d)"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
STAMP="$(studio_commander_date)"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Commander Phases Eval ($STAMP) ==="

# Phase 1
[[ -x "$DIR/cron-morning-brief.sh" ]] && record PASS "cron_morning_script" || record FAIL "cron_morning"
[[ -x "$DIR/cron-health-alert.sh" ]] && record PASS "cron_health_script" || record FAIL "cron_health"
grep -q 'cron-morning-brief' "$DIR/setup-commander-cron.sh" && record PASS "setup_commander_cron" || record FAIL "setup_commander_cron"
python3 -m py_compile "$DIR/lib/runtime_health.py" && record PASS "runtime_health_py" || record FAIL "runtime_health"
"$DIR/hermes-agent.sh" morning --date "$STAMP" --session eval 2>/dev/null | grep -qi 'Morning Pack' \
  && record PASS "morning_pack_exec" || record FAIL "morning_pack_exec"

# Phase 2
python3 <<PY && record PASS "ask_graph_router" || record FAIL "ask_graph"
import sys
sys.path.insert(0, "${DIR}")
from lib.memory_router import route_query
r = route_query("AI startup Korea", "${STAMP}")
assert r.hits, "no hits"
sources = {h.source for h in r.hits}
assert "brief_graph" in sources or "brief" in sources or "packages" in sources
assert "Brief Graph" in r.answer or "brief_graph" in r.answer or "brief" in r.answer.lower()
PY
"$DIR/hermes-agent.sh" ask "linkedin" --date "$STAMP" 2>/dev/null | grep -qi 'Memory Router' \
  && record PASS "hermes_ask_cli" || record FAIL "hermes_ask"

# Phase 3
python3 -m py_compile "$DIR/lib/publish_gate.py" && record PASS "publish_gate_py" || record FAIL "publish_gate"
"$DIR/hermes-agent.sh" pending --date "$STAMP" 2>/dev/null | grep -qiE 'HITL|대기열|Publish' \
  && record PASS "hitl_pending" || record FAIL "hitl_pending"
grep -q 'qc pending' "$WORKDIR/config/telegram-routing.yaml" && record PASS "routing_pending" || record FAIL "routing_pending"

# Phase 4 Slack parity
TG_KEYS=$(python3 -c "import yaml; d=yaml.safe_load(open('${WORKDIR}/config/telegram-routing.yaml')); print(len(d.get('quick_commands',{})))")
SL_KEYS=$(python3 -c "import yaml; d=yaml.safe_load(open('${WORKDIR}/config/slack-routing.yaml')); print(len(d.get('quick_commands',{})))")
[[ "$TG_KEYS" == "$SL_KEYS" ]] && record PASS "slack_qc_parity" || record FAIL "slack_parity ($TG_KEYS vs $SL_KEYS)"
grep -q 'pending' "$WORKDIR/config/slack-routing.yaml" && record PASS "slack_pending" || record FAIL "slack_pending"
grep -q 'Slash (intent)' "$WORKDIR/config/slack-routing.yaml" && record PASS "slack_intent_prompt" || record FAIL "slack_prompt"

echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
