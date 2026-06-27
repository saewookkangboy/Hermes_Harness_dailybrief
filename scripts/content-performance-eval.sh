#!/usr/bin/env bash
# Phase D Agent eval — M4 Performance Coach
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

echo "=== Content Performance Agents Eval (Phase D) — $STAMP ==="

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.m4_coach import run_m4_coach, _coach_linkedin, _trait_weights
" 2>/dev/null && record PASS "m4_coach_module" || record FAIL "m4_coach_module"

[[ -f "$WORKDIR/config/m4-coach.yaml" ]] && record PASS "coach_yaml" || record FAIL "coach_yaml"
[[ -x "$DIR/run-m4-coach.sh" ]] && record PASS "coach_script" || record FAIL "coach_script"
grep -q "coach:" "$WORKDIR/config/agent-commands.yaml" && record PASS "yaml_coach_intent" || record FAIL "yaml_coach_intent"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.m4_coach import run_m4_coach
r = run_m4_coach('$STAMP', days=7, write_report=True)
assert len(r.channels) == 4
assert r.stamp == '$STAMP'
" 2>/dev/null && record PASS "coach_e2e" || record FAIL "coach_e2e"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.newsletter_ctor_feedback import compute_ctor_feedback
from lib.m4_coach import _coach_newsletter, _trait_weights
fb = compute_ctor_feedback()
w = _trait_weights()
c = _coach_newsletter('$STAMP', w)
assert c.channel == 'newsletter'
" 2>/dev/null && record PASS "coach_newsletter" || record FAIL "coach_newsletter"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.m4_coach import _coach_linkedin, _trait_weights
c = _coach_linkedin('$STAMP', _trait_weights())
assert c.channel == 'linkedin'
" 2>/dev/null && record PASS "coach_linkedin" || record FAIL "coach_linkedin"

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
[[ "$FAIL" -eq 0 ]]
