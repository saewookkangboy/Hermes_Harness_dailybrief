#!/usr/bin/env bash
# Hermes Agents Eval — Phase A–D 통합 (결정적)
#
# Usage:
#   ./agents-eval.sh [YYYY-MM-DD]
#   ./agents-eval.sh              # 최신 brief 날짜
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

TOTAL_PASS=0
TOTAL_FAIL=0
PHASE_RESULTS=()

run_phase() {
  local phase="$1"
  local label="$2"
  local script="$3"
  local out rc
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if out=$("$DIR/$script" "$STAMP" 2>&1); then
    rc=0
  else
    rc=$?
  fi
  echo "$out"
  local p f
  p=$(echo "$out" | sed -n 's/.*=== \([0-9]*\) PASS · \([0-9]*\) FAIL.*/\1/p' | tail -1)
  f=$(echo "$out" | sed -n 's/.*=== \([0-9]*\) PASS · \([0-9]*\) FAIL.*/\2/p' | tail -1)
  p=${p:-0}
  f=${f:-0}
  if [[ "$rc" -ne 0 ]]; then
    f=$((f + 1))
  fi
  TOTAL_PASS=$((TOTAL_PASS + p))
  TOTAL_FAIL=$((TOTAL_FAIL + f))
  if [[ "$rc" -eq 0 && "$f" -eq 0 ]]; then
    PHASE_RESULTS+=("✅ Phase $phase ($label): ${p} PASS")
  else
    PHASE_RESULTS+=("❌ Phase $phase ($label): ${p} PASS · ${f} FAIL")
  fi
  return "$rc"
}

echo "╔══════════════════════════════════════════╗"
echo "║  Hermes Agents Eval A–D · $STAMP"
echo "╚══════════════════════════════════════════╝"

FAILED=0
run_phase A "품질" "content-quality-eval.sh" || FAILED=$((FAILED + 1))
run_phase B "운영" "content-ops-eval.sh" || FAILED=$((FAILED + 1))
run_phase C "지식" "content-knowledge-eval.sh" || FAILED=$((FAILED + 1))
run_phase D "성과" "content-performance-eval.sh" || FAILED=$((FAILED + 1))

REPORT="$WORKDIR/content/logs/${STAMP}_agents-eval-report.md"
mkdir -p "$(dirname "$REPORT")"
{
  echo "# Agents Eval A–D — $STAMP"
  echo ""
  for line in "${PHASE_RESULTS[@]}"; do
    echo "- $line"
  done
  echo ""
  echo "**Total:** $TOTAL_PASS PASS · $TOTAL_FAIL FAIL"
} >"$REPORT"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  Summary · $STAMP"
echo "╠══════════════════════════════════════════╣"
for line in "${PHASE_RESULTS[@]}"; do
  printf "║  %-40s║\n" "$line"
done
echo "╠══════════════════════════════════════════╣"
printf "║  TOTAL: %3d PASS · %3d FAIL              ║\n" "$TOTAL_PASS" "$TOTAL_FAIL"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "📋 $REPORT"

[[ "$FAILED" -eq 0 ]]
