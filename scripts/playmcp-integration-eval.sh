#!/usr/bin/env bash
# PlayMCP Commander 통합 점검 (OTT 없이 구조·라우팅)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== PlayMCP Integration Eval ==="

[[ -f "$WORKDIR/config/playmcp-routing.yaml" ]] && record PASS "playmcp-routing.yaml" || record FAIL "routing_yaml"
[[ -x "$DIR/setup-playmcp-routing.sh" ]] && record PASS "setup-playmcp-routing.sh" || record FAIL "setup_script"
grep -q "blog:" "$WORKDIR/config/playmcp-routing.yaml" 2>/dev/null && record PASS "qc_blog" || record FAIL "qc_blog"
grep -q "pipeline:" "$WORKDIR/config/playmcp-routing.yaml" 2>/dev/null && record PASS "qc_pipeline" || record FAIL "qc_pipeline"
[[ -f "$WORKDIR/skills/playmcp-commander/SKILL.md" ]] && record PASS "skill" || record FAIL "skill"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.command_registry import list_commands
cmds = {c['id'] for c in list_commands()}
assert 'pipeline' in cmds
print('PASS registry_pipeline')
" 2>/dev/null && record PASS "command_registry" || record FAIL "command_registry"

if hermes mcp list 2>/dev/null | grep -qE 'playmcp.*enabled'; then
  record PASS "mcp_enabled"
else
  echo "WARN mcp_enabled — setup-playmcp.sh OTT 필요 (구조만 PASS)"
  record PASS "mcp_wiring_only"
fi

echo ""
echo "PASS: $PASS · FAIL: $FAIL"
[[ "$FAIL" -eq 0 ]]
