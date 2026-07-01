#!/usr/bin/env bash
# 자연스러움(인간다움) eval — golden fixture + 당일 산출물 스코어
#
# Usage:
#   ./naturalness-eval.sh [YYYY-MM-DD]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

PASS=0
FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1)); echo "$1 $2"; }

echo "=== Naturalness Eval — $STAMP ==="

FIX_RESULT=$(python3 - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.naturalness_audit import run_naturalness_fixture_eval
from lib.content_quality_config import load_content_quality_config
from pathlib import Path
p, f, errs = run_naturalness_fixture_eval(Path("$WORKDIR/tests/fixtures/voice"))
min_f = int((load_content_quality_config().get("eval") or {}).get("naturalness_fixtures_min", 30))
for e in errs[:5]:
    print("ERR", e)
print(f"SUMMARY {p} {f} {min_f}")
PY
)
FP=$(echo "$FIX_RESULT" | sed -n 's/^SUMMARY \([0-9]*\).*/\1/p')
FF=$(echo "$FIX_RESULT" | sed -n 's/^SUMMARY [0-9]* \([0-9]*\).*/\1/p')
MINF=$(echo "$FIX_RESULT" | sed -n 's/^SUMMARY [0-9]* [0-9]* \([0-9]*\)/\1/p')
FP=${FP:-0}; FF=${FF:-0}; MINF=${MINF:-30}
TOTAL=$((FP + FF))
if [[ "$FF" -eq 0 && "$TOTAL" -ge "$MINF" ]]; then
  record PASS "fixtures ${FP}/${TOTAL}"
else
  record FAIL "fixtures ${FP} pass · ${FF} fail"
  echo "$FIX_RESULT" | grep "^ERR" | head -5
fi

ART_RESULT=$(python3 - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.naturalness_audit import audit_stamp_naturalness
issues = []
for ch, ns in audit_stamp_naturalness("$STAMP"):
    print(f"SCORE {ch} {ns.score} {1 if ns.passed else 0}")
    if not ns.passed:
        issues.append(f"{ch}:{ns.score}")
if issues:
    print("FAIL " + "; ".join(issues[:4]))
else:
    print("PASS artifacts")
PY
)
if echo "$ART_RESULT" | grep -q "^PASS artifacts"; then
  record PASS "channel_artifacts"
else
  record FAIL "channel_artifacts ($(echo "$ART_RESULT" | sed -n 's/^FAIL //p'))"
fi
echo "$ART_RESULT" | grep "^SCORE" | while read -r _ ch sc _ok; do
  echo "  · $ch naturalness=$sc"
done

REPORT="$WORKDIR/content/logs/${STAMP}_naturalness-eval.md"
mkdir -p "$(dirname "$REPORT")"
{
  echo "# Naturalness Eval — $STAMP"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL**"
  echo ""
  echo "## Fixture + 산출물"
  echo '```'
  echo "$FIX_RESULT"
  echo "$ART_RESULT"
  echo '```'
} >"$REPORT"

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
echo "Report: $REPORT"
[[ "$FAIL" -eq 0 ]]
