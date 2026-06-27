#!/usr/bin/env bash
# 콘텐츠 품질 Agent eval — Instagram M3 · Quality Auditor · Repurpose
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

echo "=== Content Quality Agents Eval — $STAMP ==="

[[ -x "$DIR/run-instagram-pipeline.sh" ]] && record PASS "instagram_script" || record FAIL "instagram_script"
python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.instagram_pipeline import run_instagram_pipeline
" 2>/dev/null && record PASS "instagram_module" || record FAIL "instagram_module"

[[ -x "$DIR/run-quality-audit.sh" ]] && record PASS "audit_script" || record FAIL "audit_script"
python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.quality_auditor import run_quality_audit
" 2>/dev/null && record PASS "audit_module" || record FAIL "audit_module"

[[ -x "$DIR/run-repurpose.sh" ]] && record PASS "repurpose_script" || record FAIL "repurpose_script"
python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.repurpose_pipeline import run_repurpose, VALID_CHANNELS
assert 'linkedin' in VALID_CHANNELS
" 2>/dev/null && record PASS "repurpose_module" || record FAIL "repurpose_module"

grep -q "instagram:" "$WORKDIR/config/agent-commands.yaml" && record PASS "yaml_instagram_intent" || record FAIL "yaml_instagram_intent"
grep -q "audit:" "$WORKDIR/config/agent-commands.yaml" && record PASS "yaml_audit_intent" || record FAIL "yaml_audit_intent"
grep -q "repurpose:" "$WORKDIR/config/agent-commands.yaml" && record PASS "yaml_repurpose_intent" || record FAIL "yaml_repurpose_intent"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.instagram_pipeline import run_instagram_pipeline
r = run_instagram_pipeline('$STAMP', validate=False)
assert r.get('instagram_md')
" 2>/dev/null && record PASS "instagram_e2e" || record FAIL "instagram_e2e"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.quality_auditor import audit_stamp
r = audit_stamp('$STAMP', write_report=True)
assert r.stamp == '$STAMP'
" 2>/dev/null && record PASS "audit_e2e" || record FAIL "audit_e2e"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.repurpose_pipeline import run_repurpose
r = run_repurpose('$STAMP', 'linkedin', 1, validate=False)
assert r.get('artifacts')
" 2>/dev/null && record PASS "repurpose_e2e" || record FAIL "repurpose_e2e"

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
[[ "$FAIL" -eq 0 ]]
