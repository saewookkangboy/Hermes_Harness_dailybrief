#!/usr/bin/env bash
# Phase 3 — Command Registry · Brief Graph · HITL Publish Gate eval
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

REPORT="$WORKDIR/content/logs/${STAMP}_phase3-eval-report.md"
mkdir -p "$WORKDIR/content/logs"

run_py() {
  if [[ -x "$HERMES_PY" ]]; then "$HERMES_PY" "$@"
  else python3 "$@"; fi
}

PASS=0
FAIL=0
RESULT_LINES=()

record() {
  local status="$1" name="$2" detail="$3"
  if [[ "$status" == "PASS" ]]; then PASS=$((PASS + 1)); else FAIL=$((FAIL + 1)); fi
  RESULT_LINES+=("| $status | $name | $detail |")
}

echo "=== Phase 3 Eval ==="

# --- Command registry ---
REG=$(run_py "$DIR/hermes-agent.py" commands --session phase3-eval 2>&1)
if echo "$REG" | grep -qE "Command Registry|pipeline|notion-sync"; then
  record PASS "command_registry" "intents+commands"
else
  record FAIL "command_registry" "$REG"
fi

# --- Brief graph ---
GRAPH=$(run_py "$DIR/hermes-agent.py" graph --date "$STAMP" --write-unified --session phase3-eval 2>&1)
if [[ -f "$WORKDIR/content/research/_brief_graph.json" ]]; then
  record PASS "brief_graph" "_brief_graph.json"
else
  record FAIL "brief_graph" "$GRAPH"
fi

if grep -q "이전 브리프와의 차이" "$WORKDIR/content/packages/${STAMP}_unified-context.md" 2>/dev/null; then
  record PASS "unified_graph_column" "diff column"
else
  record FAIL "unified_graph_column" "graph table missing"
fi

# --- HITL gate (pending) ---
GATE=$(run_py "$DIR/hermes-agent.py" publish linkedin --date "$STAMP" --session phase3-eval 2>&1)
if echo "$GATE" | grep -q "HITL Publish Gate" && [[ -f "$WORKDIR/.harness/publish-queue/${STAMP}.json" ]]; then
  record PASS "hitl_gate" "pending queue"
else
  record FAIL "hitl_gate" "$GATE"
fi

# --- HITL approve (dry: queue state only — skip full notion) ---
run_py -c "
import sys
sys.path.insert(0, '$DIR')
from lib.publish_gate import approve_channels, load_queue
approve_channels('$STAMP', ['linkedin'])
q = load_queue('$STAMP')
assert q['channels'].get('linkedin') == 'approved'
print('approved')
" >/dev/null 2>&1 && record PASS "hitl_approve" "linkedin approved" || record FAIL "hitl_approve" "approve failed"

# --- run registry (dry check script exists) ---
if [[ -x "$DIR/run-research-brief.sh" ]] && run_py -c "
import sys
sys.path.insert(0, '$DIR')
from lib.command_registry import resolve_command
assert resolve_command('pipeline') is not None
assert resolve_command('notion-sync') is not None
"; then
  record PASS "registry_resolve" "pipeline+notion-sync"
else
  record FAIL "registry_resolve" "resolve failed"
fi

# --- Phase 2 regression ---
if SKIP_INIT=1 "$DIR/phase2-eval.sh" "$STAMP" >>/tmp/phase3-phase2.log 2>&1; then
  record PASS "phase2_regression" "8/8 still OK"
else
  record FAIL "phase2_regression" "see /tmp/phase3-phase2.log"
fi

{
  echo "# Phase 3 Eval Report — $STAMP"
  echo ""
  echo "생성: $(date '+%Y-%m-%d %H:%M:%S') KST"
  echo ""
  echo "## 요약"
  echo "- PASS: **$PASS**"
  echo "- FAIL: **$FAIL**"
  echo ""
  echo "## 결과 테이블"
  echo "| Status | Test | Detail |"
  echo "|--------|------|--------|"
  for line in "${RESULT_LINES[@]}"; do echo "$line"; done
  echo ""
  echo "## 샘플 출력 (코드복사용)"
  echo ""
  echo "### Command Registry"
  echo '```'
  echo "$REG" | head -20
  echo '```'
  echo ""
  echo "### Brief Graph"
  echo '```'
  echo "$GRAPH"
  echo '```'
  echo ""
  echo "### HITL Gate"
  echo '```'
  echo "$GATE"
  echo '```'
  echo ""
  echo "### Unified Context (Graph 발췌)"
  echo '```'
  grep -A 8 "Research Brief 발췌 (Graph)" "$WORKDIR/content/packages/${STAMP}_unified-context.md" 2>/dev/null | head -12 || echo N/A
  echo '```'
} > "$REPORT"

echo ""
echo "Report: $REPORT"
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
