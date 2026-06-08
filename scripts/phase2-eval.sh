#!/usr/bin/env bash
# Phase 2 Agent 고도화 — M4 traces · LinkedIn M3 · Session handoff eval
#
# Usage:
#   ./phase2-eval.sh [YYYY-MM-DD]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

REPORT="$WORKDIR/content/logs/${STAMP}_phase2-eval-report.md"
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

echo "=== Phase 2 Eval ==="

# --- M4 traces ---
T0=$(date +%s)
M4=$(run_py "$DIR/hermes-agent.py" traces --days 7 --session phase2-eval 2>&1)
M4_MS=$(python3 -c "print(($(date +%s)-$T0)*1000)" 2>/dev/null || echo "0")
if echo "$M4" | grep -qE "M4 Performance|트레이스"; then
  record PASS "m4_traces" "${M4_MS}ms"
else
  record FAIL "m4_traces" "$(echo "$M4" | head -2)"
fi

# --- LinkedIn M3 pipeline ---
T0=$(date +%s)
LI=$(run_py "$DIR/hermes-agent.py" linkedin --date "$STAMP" --session phase2-eval 2>&1)
LI_MS=$(python3 -c "print(($(date +%s)-$T0)*1000)" 2>/dev/null || echo "0")
if [[ -f "$WORKDIR/content/packages/${STAMP}_linkedin-analysis.md" ]] \
  && [[ -f "$WORKDIR/content/packages/${STAMP}_linkedin-strategy.md" ]]; then
  record PASS "linkedin_m3" "${LI_MS}ms · analysis+strategy"
else
  record FAIL "linkedin_m3" "$LI"
fi

# --- LinkedIn context M3 section ---
if grep -q "## M3 전략 요약" "$WORKDIR/content/packages/${STAMP}_linkedin-context.md" 2>/dev/null; then
  record PASS "linkedin_context_m3" "strategy section"
else
  record FAIL "linkedin_context_m3" "M3 section missing"
fi

# --- Handoff JSON ---
if [[ -f "$WORKDIR/.harness/handoffs/${STAMP}_linkedin-M3.json" ]]; then
  record PASS "handoff_json" "M3 handoff"
else
  record FAIL "handoff_json" "missing"
fi

# --- Session handoff md ---
HO=$(run_py "$DIR/hermes-agent.py" handoff --session phase2-eval 2>&1)
if [[ -f "$WORKDIR/.harness/session-handoff.md" ]] && grep -q "Phase 2" "$WORKDIR/.harness/session-handoff.md"; then
  record PASS "session_handoff" "session-handoff.md"
else
  record FAIL "session_handoff" "$HO"
fi

# --- Resume block ---
RESUME=$(run_py -c "
import sys
sys.path.insert(0, '$DIR')
from lib.session_handoff import format_resume_block
print(format_resume_block('phase2-eval'))
" 2>&1)
if echo "$RESUME" | grep -q "다음 제안"; then
  record PASS "resume_block" "actionable hints"
else
  record FAIL "resume_block" "$RESUME"
fi

# --- M4 snapshot ---
if [[ -f "$WORKDIR/.harness/m4-snapshot.json" ]]; then
  record PASS "m4_snapshot" "m4-snapshot.json"
else
  record FAIL "m4_snapshot" "missing"
fi

# --- Phase 1 regression ---
if SKIP_INIT=1 "$DIR/phase1-eval.sh" "$STAMP" >>/tmp/phase2-phase1.log 2>&1; then
  record PASS "phase1_regression" "8/8 still OK"
else
  record FAIL "phase1_regression" "see /tmp/phase2-phase1.log"
fi

# --- Write report ---
{
  echo "# Phase 2 Eval Report — $STAMP"
  echo ""
  echo "생성: $(date '+%Y-%m-%d %H:%M:%S') KST"
  echo ""
  echo "## 요약"
  echo ""
  echo "- PASS: **$PASS**"
  echo "- FAIL: **$FAIL**"
  echo ""
  echo "## 결과 테이블"
  echo ""
  echo "| Status | Test | Detail |"
  echo "|--------|------|--------|"
  for line in "${RESULT_LINES[@]}"; do echo "$line"; done
  echo ""
  echo "## 샘플 출력 (코드복사용)"
  echo ""
  echo "### M4 Traces"
  echo '```'
  echo "$M4"
  echo '```'
  echo ""
  echo "### LinkedIn M3 Pipeline"
  echo '```'
  echo "$LI"
  echo '```'
  echo ""
  echo "### LinkedIn Strategy (발췌)"
  echo '```'
  head -25 "$WORKDIR/content/packages/${STAMP}_linkedin-strategy.md" 2>/dev/null || echo "N/A"
  echo '```'
  echo ""
  echo "### Session Handoff (발췌)"
  echo '```'
  head -35 "$WORKDIR/.harness/session-handoff.md" 2>/dev/null || echo "N/A"
  echo '```'
  echo ""
  echo "### Resume Block"
  echo '```'
  echo "$RESUME"
  echo '```'
  echo ""
  echo "## 다음 단계 (Phase 3)"
  echo ""
  echo "FAIL=0 확인 후: Agent command registry · Brief Graph · HITL publish gate"
} > "$REPORT"

echo ""
echo "Report: $REPORT"
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
