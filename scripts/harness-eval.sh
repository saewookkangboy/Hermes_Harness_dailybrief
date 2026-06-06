#!/usr/bin/env bash
# Hermes Content Studio — Harness Performance Eval
#
# awesome-harness-engineering 기반 성능 기준선·회귀 검출
#
# Usage:
#   ./harness-eval.sh           # 전체 eval (research + content)
#   ./harness-eval.sh --quick   # 구조 검증만 (빠름)
#   ./harness-eval.sh --record  # 결과를 .harness/eval-results.json 저장
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
MODE="full"
RECORD=0

for arg in "$@"; do
  case "$arg" in
    --quick) MODE="quick" ;;
    --record) RECORD=1 ;;
  esac
done

run_python() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

echo "=== Harness Eval (v1.2.0) ==="
echo "모드: $MODE"
echo ""

PASS=0
FAIL=0
WARN=0
RESULTS=()

check_struct() {
  local name="$1" path="$2"
  if [[ -e "$path" ]]; then
    echo "✅ $name"
    PASS=$((PASS + 1))
    return 0
  fi
  echo "❌ $name — $path"
  FAIL=$((FAIL + 1))
  return 1
}

warn_check() {
  local name="$1" path="$2"
  if [[ -e "$path" ]]; then
    echo "✅ $name"
    PASS=$((PASS + 1))
  else
    echo "⚠️  $name — $path"
    WARN=$((WARN + 1))
  fi
}

echo "--- Harness 5-Subsystem ---"
check_struct "Instructions (AGENTS.md)" "$WORKDIR/AGENTS.md"
check_struct "Harness spec (HARNESS.md)" "$WORKDIR/HARNESS.md"
check_struct "State (feature_list)" "$WORKDIR/.harness/feature_list.json"
check_struct "State (progress)" "$WORKDIR/.harness/progress.md"
check_struct "Verification (init.sh)" "$DIR/init.sh"
check_struct "Verification (validate-output)" "$DIR/validate-output.sh"
check_struct "Config (harness.yaml)" "$WORKDIR/config/harness.yaml"
warn_check "Lifecycle (session-handoff)" "$WORKDIR/.harness/session-handoff.md"
warn_check "Observability (traces)" "$WORKDIR/.harness/traces"

if [[ "$MODE" == "quick" ]]; then
  echo ""
  echo "=== Quick eval: ✅ $PASS / ❌ $FAIL / ⚠️ $WARN ==="
  [[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
fi

echo ""
echo "--- Performance Benchmark ---"
DATE=$(date +%Y-%m-%d)
BRIEF="$WORKDIR/content/research/${DATE}_brief.md"

# Research timing
RESEARCH_START=$(date +%s)
"$DIR/run-research-brief.sh" >/tmp/harness-eval-research.log 2>&1
RESEARCH_END=$(date +%s)
RESEARCH_ELAPSED=$(( RESEARCH_END - RESEARCH_START ))
echo "리서치: ${RESEARCH_ELAPSED}s"
RESULTS+=("research:${RESEARCH_ELAPSED}")

# Content timing
CONTENT_START=$(date +%s)
"$DIR/run-content-package.sh" "$DATE" >/tmp/harness-eval-content.log 2>&1
CONTENT_END=$(date +%s)
CONTENT_ELAPSED=$(( CONTENT_END - CONTENT_START ))
echo "콘텐츠: ${CONTENT_ELAPSED}s"
RESULTS+=("content:${CONTENT_ELAPSED}")

FULL_ELAPSED=$(( RESEARCH_ELAPSED + CONTENT_ELAPSED ))
echo "합계 (research+content): ${FULL_ELAPSED}s"
RESULTS+=("full_pipeline:${FULL_ELAPSED}")

# Regression check via Python
echo ""
echo "--- Regression Check ---"
REGRESSION_JSON=$(run_python -c "
import sys
sys.path.insert(0, '$DIR/lib')
from harness import check_regression, save_eval_results
import json

results = {
    'mode': '$MODE',
    'stages': [
        check_regression('research', $RESEARCH_ELAPSED),
        check_regression('content', $CONTENT_ELAPSED),
        check_regression('full_pipeline', $FULL_ELAPSED),
    ],
}
for r in results['stages']:
    flag = '⚠️ REGRESSION' if r.get('regression') else '✅ OK'
    print(f\"{flag} {r['stage']}: {r.get('elapsed', '?')}s (baseline {r.get('baseline', '?')}s, delta {r.get('delta_pct', 0)}%)\")
if $RECORD:
    path = save_eval_results(results)
    print(f'Recorded: {path}')
print(json.dumps(results))
" 2>&1)

echo "$REGRESSION_JSON" | grep -E '^(✅|⚠️|Recorded)' || true

if echo "$REGRESSION_JSON" | grep -q '"regression": true'; then
  WARN=$((WARN + 1))
  echo "⚠️  성능 회귀 감지 — config/harness.yaml eval.baseline_seconds 확인"
fi

echo ""
echo "=== Eval 결과: ✅ $PASS / ❌ $FAIL / ⚠️ $WARN ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
