#!/usr/bin/env bash
# M1~M5 결정적 파이프라인 무결성 검증 — JARVIS/EasyTool 작업이 파이프라인을 건드리지 않았는지 확인
#
# Usage: ./pipeline-integrity-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
PASS=0
FAIL=0

record() { [[ "$1" == PASS ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1)); echo "$1 $2"; }

echo "=== Pipeline Integrity Eval (M1~M5) ==="

PIPELINE_FILES=(
  "scripts/run-pipeline.sh"
  "scripts/run-research-brief.sh"
  "scripts/run-content-package.sh"
  "scripts/run-newsletter.sh"
  "scripts/assemble-research-brief.py"
  "scripts/assemble-content-package.py"
  "scripts/assemble-newsletter.py"
)

for f in "${PIPELINE_FILES[@]}"; do
  if [[ -f "$WORKDIR/$f" ]]; then
    record PASS "exists_${f##*/}"
  else
    record FAIL "missing_${f##*/}"
  fi
done

# assemble-*.py must remain deterministic (no LLM API imports)
for asm in assemble-research-brief.py assemble-content-package.py assemble-newsletter.py; do
  if grep -qE "openai|anthropic|ollama|hermes-run|codex" "$DIR/$asm" 2>/dev/null; then
    record FAIL "${asm}_llm_import"
  else
    record PASS "${asm}_deterministic"
  fi
done

# run-pipeline.sh wiring
if grep -q "run-research-brief.sh" "$DIR/run-pipeline.sh" \
  && grep -q "run-content-package.sh" "$DIR/run-pipeline.sh" \
  && grep -q "assemble-research-brief.py" "$DIR/run-research-brief.sh"; then
  record PASS "pipeline_wiring"
else
  record FAIL "pipeline_wiring"
fi

# harness.yaml deterministic_first
if grep -q "deterministic_first: true" "$WORKDIR/config/harness.yaml"; then
  record PASS "harness_deterministic_first"
else
  record FAIL "harness_deterministic_first"
fi

# feature_list pipe-001~005 still passing
if command -v jq >/dev/null 2>&1; then
  for pid in pipe-001 pipe-002 pipe-003 pipe-004 pipe-005; do
    st=$(jq -r --arg id "$pid" '.features[] | select(.id==$id) | .status' "$WORKDIR/.harness/feature_list.json" 2>/dev/null || echo "")
    if [[ "$st" == "passing" ]]; then
      record PASS "feature_${pid}"
    else
      record FAIL "feature_${pid}_status=${st:-missing}"
    fi
  done
fi

echo ""
echo "=== Summary: $PASS pass, $FAIL fail ==="
[[ "$FAIL" -eq 0 ]]
