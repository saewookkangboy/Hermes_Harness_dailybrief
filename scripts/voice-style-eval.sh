#!/usr/bin/env bash
# Voice / 문체 품질 eval — AI-tell · ellipsis · LinkedIn 불릿 완결성
#
# Usage:
#   ./voice-style-eval.sh [YYYY-MM-DD]
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

echo "=== Voice Style Eval — $STAMP ==="

FIXTURE_RESULT=$(python3 - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.voice_style_audit import run_fixture_eval
from pathlib import Path
p, f, errs = run_fixture_eval(Path("$WORKDIR/tests/fixtures/voice"))
for e in errs[:5]:
    print("ERR", e)
print(f"SUMMARY {p} {f}")
PY
)
FP=$(echo "$FIXTURE_RESULT" | sed -n 's/^SUMMARY \([0-9]*\) \([0-9]*\)/\1/p')
FF=$(echo "$FIXTURE_RESULT" | sed -n 's/^SUMMARY \([0-9]*\) \([0-9]*\)/\2/p')
FP=${FP:-0}
FF=${FF:-0}
MIN_FIX=$(( $(python3 -c "import sys; sys.path.insert(0, '$DIR'); from lib.content_quality_config import load_content_quality_config; print((load_content_quality_config().get('eval') or {}).get('voice_fixtures_min', 50))") ))
if [[ "$FF" -eq 0 && "$FP" -ge "$MIN_FIX" ]]; then
  record PASS "fixtures ${FP}/${MIN_FIX}"
else
  record FAIL "fixtures ${FP} pass · ${FF} fail (min ${MIN_FIX})"
  echo "$FIXTURE_RESULT" | grep "^ERR" | head -5
fi

CHANGE_RESULT=$(python3 - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.voice_style_audit import run_change_rate_eval
from pathlib import Path
p, f, errs = run_change_rate_eval(Path("$WORKDIR/tests/fixtures/voice"))
for e in errs[:5]:
    print("ERR", e)
print(f"SUMMARY {p} {f}")
PY
)
CP=$(echo "$CHANGE_RESULT" | sed -n 's/^SUMMARY \([0-9]*\) \([0-9]*\)/\1/p')
CF=$(echo "$CHANGE_RESULT" | sed -n 's/^SUMMARY \([0-9]*\) \([0-9]*\)/\2/p')
CP=${CP:-0}
CF=${CF:-0}
if [[ "$CF" -eq 0 && "$CP" -ge "$MIN_FIX" ]]; then
  record PASS "change_rate ${CP}/${MIN_FIX}"
else
  record FAIL "change_rate ${CP} pass · ${CF} fail"
  echo "$CHANGE_RESULT" | grep "^ERR" | head -5
fi

BUILDER_RESULT=$(python3 - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.voice_style_audit import run_linkedin_builder_eval
p, f, errs = run_linkedin_builder_eval("$STAMP")
for e in errs[:3]:
    print("ERR", e)
print(f"SUMMARY {p} {f}")
PY
)
if echo "$BUILDER_RESULT" | grep -q "^SUMMARY 1 0"; then
  record PASS "linkedin_builder"
else
  record FAIL "linkedin_builder"
  echo "$BUILDER_RESULT" | grep "^ERR" | head -3
fi

LI=$(ls -1 "$WORKDIR/content/linkedin/${STAMP}"_linkedin_*.md 2>/dev/null | head -1)
if [[ -n "$LI" && -f "$LI" ]]; then
  FILE_RESULT=$(python3 - <<PY
import sys
sys.path.insert(0, "$DIR")
from pathlib import Path
from lib.voice_style_audit import audit_linkedin_file
issues = audit_linkedin_file(Path("$LI"))
for i in issues[:3]:
    print("ERR", i)
print(f"SUMMARY {0 if issues else 1} {1 if issues else 0}")
PY
  )
  if echo "$FILE_RESULT" | grep -q "^SUMMARY 1 0"; then
    record PASS "linkedin_artifact"
  else
    record FAIL "linkedin_artifact"
    echo "$FILE_RESULT" | grep "^ERR" | head -3
  fi
else
  record FAIL "linkedin_artifact (파일 없음)"
fi

IG=$(ls -1 "$WORKDIR/content/instagram/${STAMP}"_instagram_*.md 2>/dev/null | head -1)
if [[ -n "$IG" && -f "$IG" ]]; then
  IG_RESULT=$(python3 - <<PY
import sys
sys.path.insert(0, "$DIR")
from pathlib import Path
from lib.voice_style_audit import audit_instagram_file
issues = audit_instagram_file(Path("$IG"))
for i in issues[:3]:
    print("ERR", i)
print(f"SUMMARY {0 if issues else 1} {1 if issues else 0}")
PY
  )
  if echo "$IG_RESULT" | grep -q "^SUMMARY 1 0"; then
    record PASS "instagram_artifact"
  else
    record FAIL "instagram_artifact"
    echo "$IG_RESULT" | grep "^ERR" | head -3
  fi
else
  record FAIL "instagram_artifact (파일 없음)"
fi

REPORT="$WORKDIR/content/logs/${STAMP}_voice-style-eval.md"
mkdir -p "$(dirname "$REPORT")"
{
  echo "# Voice Style Eval — $STAMP"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL**"
  echo ""
  echo "## 범위"
  echo "- AI-tell fixture ${MIN_FIX}건 + change_rate cap"
  echo "- build_linkedin_post_text 완결 문장"
  echo "- LinkedIn · Instagram 산출물 artifact 감사"
} >"$REPORT"

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
echo "Report: $REPORT"
[[ "$FAIL" -eq 0 ]]
