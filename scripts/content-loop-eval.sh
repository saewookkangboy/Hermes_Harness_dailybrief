#!/usr/bin/env bash
# Content Loop Engineering rubric — 콘텐츠 공장 맞춤 (loop-audit 대체)
#
# Usage:
#   ./content-loop-eval.sh [YYYY-MM-DD]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"

OUT=$(python3 - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.content_loop_rubric import run_content_loop_rubric, write_rubric_report
r = run_content_loop_rubric()
path = write_rubric_report("$STAMP")
print(f"SCORE {r.score} {r.max_score} {r.level} {r.target} {1 if r.passed else 0}")
print(f"REPORT {path}")
PY
)

SCORE=$(echo "$OUT" | sed -n 's/^SCORE \([0-9]*\).*/\1/p')
MAX=$(echo "$OUT" | sed -n 's/^SCORE [0-9]* \([0-9]*\).*/\1/p')
LEVEL=$(echo "$OUT" | sed -n 's/^SCORE [0-9]* [0-9]* \([^ ]*\).*/\1/p')
TARGET=$(echo "$OUT" | sed -n 's/^SCORE [0-9]* [0-9]* [^ ]* \([0-9]*\).*/\1/p')
PASSED=$(echo "$OUT" | sed -n 's/^SCORE .* \([01]\)$/\1/p')
REPORT=$(echo "$OUT" | sed -n 's/^REPORT //p')

echo "=== Content Loop Rubric — $STAMP ==="
echo "Score: $SCORE / $MAX ($LEVEL) · target $TARGET+"
echo "Report: $REPORT"

if [[ "$PASSED" == "1" ]]; then
  echo "✅ PASS (≥${TARGET})"
  exit 0
fi
echo "⚠️  BELOW TARGET (${TARGET}+)"
exit 1
