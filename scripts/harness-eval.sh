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
check_struct "Config (content-quality.yaml)" "$WORKDIR/config/content-quality.yaml"
check_struct "Voice eval (voice-style-eval)" "$DIR/voice-style-eval.sh"
check_struct "Naturalness eval (naturalness-eval)" "$DIR/naturalness-eval.sh"
check_struct "Loop budget eval (loop-budget-eval)" "$DIR/loop-budget-eval.sh"
check_struct "Loop budget status (loop-budget-status)" "$DIR/loop-budget-status.sh"
check_struct "Humanize LLM eval (humanize-llm-eval)" "$DIR/humanize-llm-eval.sh"
check_struct "M5 Notion eval (m5-notion-eval)" "$DIR/m5-notion-eval.sh"
check_struct "Staging supervised eval" "$DIR/staging-supervised-eval.sh"
check_struct "PlayMCP routing E2E" "$DIR/playmcp-routing-e2e.sh"
check_struct "Content loop eval (content-loop-eval)" "$DIR/content-loop-eval.sh"
check_struct "Newsletter pipeline (run-newsletter)" "$DIR/run-newsletter.sh"
check_struct "Newsletter eval (newsletter-eval)" "$DIR/newsletter-eval.sh"
check_struct "Newsletter config" "$WORKDIR/config/newsletter.yaml"
check_struct "Newsletter feature (pipe-008)" "$WORKDIR/.harness/feature_list.json"
warn_check "Lifecycle (session-handoff)" "$WORKDIR/.harness/session-handoff.md"
warn_check "Observability (traces)" "$WORKDIR/.harness/traces"

if command -v jq >/dev/null 2>&1; then
  if jq -e '.features[] | select(.id=="pipe-008" and .area=="newsletter")' \
    "$WORKDIR/.harness/feature_list.json" >/dev/null 2>&1; then
    echo "✅ feature pipe-008 (newsletter)"
    PASS=$((PASS + 1))
  else
    echo "❌ feature pipe-008 (newsletter) — feature_list.json"
    FAIL=$((FAIL + 1))
  fi
  if jq -e '.features[] | select(.id=="pipe-015" and .area=="quality")' \
    "$WORKDIR/.harness/feature_list.json" >/dev/null 2>&1; then
    echo "✅ feature pipe-015 (voice-naturalness)"
    PASS=$((PASS + 1))
  else
    echo "❌ feature pipe-015 (voice-naturalness) — feature_list.json"
    FAIL=$((FAIL + 1))
  fi
fi

if [[ "$MODE" == "quick" ]]; then
  if "$DIR/loop-budget-eval.sh" >/tmp/harness-loop-budget.log 2>&1; then
    echo "✅ loop-budget-eval"
    PASS=$((PASS + 1))
  else
    echo "❌ loop-budget-eval"
    FAIL=$((FAIL + 1))
  fi
  if "$DIR/humanize-llm-eval.sh" >/tmp/harness-humanize-llm.log 2>&1; then
    echo "✅ humanize-llm-eval (wiring)"
    PASS=$((PASS + 1))
  else
    echo "❌ humanize-llm-eval (wiring)"
    FAIL=$((FAIL + 1))
  fi
  if "$DIR/m5-notion-eval.sh" >/tmp/harness-m5-notion.log 2>&1; then
    echo "✅ m5-notion-eval (wiring)"
    PASS=$((PASS + 1))
  else
    echo "❌ m5-notion-eval (wiring)"
    FAIL=$((FAIL + 1))
  fi
  if "$DIR/playmcp-routing-e2e.sh" >/tmp/harness-playmcp-routing.log 2>&1; then
    echo "✅ playmcp-routing-e2e (wiring)"
    PASS=$((PASS + 1))
  else
    echo "❌ playmcp-routing-e2e (wiring)"
    FAIL=$((FAIL + 1))
  fi
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

NEWSLETTER_START=$(date +%s)
SKIP_INIT=1 "$DIR/run-newsletter.sh" "$DATE" >/tmp/harness-eval-newsletter.log 2>&1 || true
NEWSLETTER_END=$(date +%s)
NEWSLETTER_ELAPSED=$(( NEWSLETTER_END - NEWSLETTER_START ))
echo "뉴스레터: ${NEWSLETTER_ELAPSED}s"
RESULTS+=("newsletter:${NEWSLETTER_ELAPSED}")

FULL_ELAPSED=$(( RESEARCH_ELAPSED + CONTENT_ELAPSED + NEWSLETTER_ELAPSED ))
echo "합계 (research+content+newsletter): ${FULL_ELAPSED}s"
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
        check_regression('newsletter', $NEWSLETTER_ELAPSED),
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
