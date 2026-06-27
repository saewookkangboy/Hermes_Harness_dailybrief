#!/usr/bin/env bash
# Phase C Agent eval — Wiki Curator · Research Squad · Competitive Watch
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

echo "=== Content Knowledge Agents Eval (Phase C) — $STAMP ==="

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.wiki_curator import run_wiki_curator, lint_wiki
" 2>/dev/null && record PASS "wiki_curator_module" || record FAIL "wiki_curator_module"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.research_squad import run_research_squad
" 2>/dev/null && record PASS "research_squad_module" || record FAIL "research_squad_module"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.competitive_watch import run_competitive_watch
" 2>/dev/null && record PASS "competitive_watch_module" || record FAIL "competitive_watch_module"

[[ -f "$WORKDIR/config/competitive-watch.yaml" ]] && record PASS "watch_yaml" || record FAIL "watch_yaml"
[[ -x "$DIR/run-wiki-curator.sh" ]] && record PASS "wiki_curator_script" || record FAIL "wiki_curator_script"
[[ -x "$DIR/cron-competitive-watch.sh" ]] && record PASS "watch_cron" || record FAIL "watch_cron"

grep -q "wiki:" "$WORKDIR/config/agent-commands.yaml" && record PASS "yaml_wiki_intent" || record FAIL "yaml_wiki_intent"
grep -q "squad:" "$WORKDIR/config/agent-commands.yaml" && record PASS "yaml_squad_intent" || record FAIL "yaml_squad_intent"
grep -q "watch:" "$WORKDIR/config/agent-commands.yaml" && record PASS "yaml_watch_intent" || record FAIL "yaml_watch_intent"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.wiki_curator import lint_wiki
r = lint_wiki(write_report=True)
assert 'issue_count' in r
" 2>/dev/null && record PASS "wiki_lint_e2e" || record FAIL "wiki_lint_e2e"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.research_squad import run_research_squad
r = run_research_squad('AX 트렌드', '$STAMP')
assert len(r.roles) == 4
" 2>/dev/null && record PASS "squad_e2e" || record FAIL "squad_e2e"

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.competitive_watch import run_competitive_watch
r = run_competitive_watch(write_report=True)
assert r.get('report_path')
" 2>/dev/null && record PASS "watch_e2e" || record FAIL "watch_e2e"

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
[[ "$FAIL" -eq 0 ]]
