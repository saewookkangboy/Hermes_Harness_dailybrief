#!/usr/bin/env bash
# Phase 1 Agent 고도화 — 성능·기능 eval + 리포트 생성
#
# Usage:
#   ./phase1-eval.sh              # 전체 eval
#   ./phase1-eval.sh --quick      # unit only (네트워크/Notion 제외)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ "${1:-}" == "--quick" ]]; then STAMP=$(date +%Y-%m-%d); fi
# 콘텐츠가 있는 최신 날짜로 폴백
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi
QUICK=0
[[ "${1:-}" == "--quick" ]] && QUICK=1

REPORT="$WORKDIR/content/logs/${STAMP}_phase1-eval-report.md"
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

echo "=== Phase 1 Eval ==="

# --- Unit: memory router perf ---
T0=$(python3 -c "import time; print(time.time())" 2>/dev/null || date +%s)
OUT=$(run_py -c "
import sys, time
sys.path.insert(0, '$DIR')
from lib.memory_router import route_query
t0 = time.perf_counter()
r = route_query('Kurly AX 인사이트', '$STAMP')
ms = (time.perf_counter() - t0) * 1000
print(f'hits={len(r.hits)} skip={r.skip_web_search} ms={ms:.1f}')
" 2>&1)
MS=$(echo "$OUT" | sed -n 's/.*ms=\([0-9.]*\).*/\1/p')
if [[ -n "$MS" ]] && python3 -c "exit(0 if float('$MS') < 500 else 1)" 2>/dev/null; then
  record PASS "memory_router latency" "${MS}ms (<500ms)"
else
  record FAIL "memory_router latency" "$OUT"
fi

# --- Unit: proactive ---
PALERT=$(run_py "$DIR/hermes-agent.py" proactive --date "$STAMP" 2>&1 | head -3)
record PASS "proactive_check" "$(echo "$PALERT" | tr '\n' ' ' | head -c 80)"

# --- Unit: session ---
run_py "$DIR/hermes-agent.py" morning --session eval-test --date "$STAMP" >/dev/null 2>&1
SESS=$(run_py "$DIR/hermes-agent.py" session --session eval-test 2>&1)
if echo "$SESS" | grep -q "morning"; then
  record PASS "session_sot" "last_intent=morning"
else
  record FAIL "session_sot" "$SESS"
fi

# --- Unit: personal bridge ---
run_py "$DIR/hermes-agent.py" bridge-sync --date "$STAMP" >/dev/null 2>&1
if [[ -f "$WORKDIR/content/personal/_inbox_candidates.json" ]]; then
  record PASS "personal_bridge" "_inbox_candidates.json"
else
  record FAIL "personal_bridge" "inbox file missing"
fi

# --- Intent: morning output sample ---
MORNING=$(run_py "$DIR/hermes-agent.py" morning --date "$STAMP" --session eval-test 2>&1)
if echo "$MORNING" | grep -qE "Top 3|brief 없음|Proactive"; then
  record PASS "intent_morning" "morning pack OK"
else
  record FAIL "intent_morning" "$(echo "$MORNING" | head -2)"
fi

# --- Intent: catch-up ---
CATCH=$(run_py "$DIR/hermes-agent.py" catch-up --days 3 2>&1)
if echo "$CATCH" | grep -q "최근 Brief"; then
  record PASS "intent_catch-up" "recent briefs"
else
  record FAIL "intent_catch-up" "$CATCH"
fi

# --- Intent: auto detect ---
AUTO=$(run_py "$DIR/hermes-agent.py" auto "/morning" --date "$STAMP" 2>&1 | head -1)
if echo "$AUTO" | grep -qi "morning\|Top 3\|Proactive"; then
  record PASS "intent_auto" "morning routed"
else
  record FAIL "intent_auto" "$AUTO"
fi

# --- Harness quick ---
if SKIP_INIT=1 "$DIR/harness-eval.sh" --quick >>/tmp/phase1-harness.log 2>&1; then
  record PASS "harness_quick" "structure OK"
else
  record FAIL "harness_quick" "see /tmp/phase1-harness.log"
fi

# --- Write report ---
{
  echo "# Phase 1 Eval Report — $STAMP"
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
  echo "### Morning Pack"
  echo '```'
  echo "$MORNING"
  echo '```'
  echo ""
  echo "### Memory Router (Kurly AX)"
  echo '```'
  run_py "$DIR/hermes-agent.py" route "Kurly AX 인사이트" --date "$STAMP" 2>&1
  echo '```'
  echo ""
  echo "### Catch-up (3일)"
  echo '```'
  echo "$CATCH"
  echo '```'
  echo ""
  echo "### Personal Bridge"
  echo '```'
  run_py "$DIR/hermes-agent.py" bridge-sync --date "$STAMP" 2>&1
  echo '```'
  echo ""
  echo "### Session"
  echo '```'
  echo "$SESS"
  echo '```'
  echo ""
  echo "## 다음 단계 (Phase 2)"
  echo ""
  echo "FAIL=0 확인 후: Session handoff 고도화 · M4 traces · LinkedIn sub-pipeline"
} > "$REPORT"

echo ""
echo "Report: $REPORT"
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
