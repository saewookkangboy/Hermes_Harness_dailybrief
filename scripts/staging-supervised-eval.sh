#!/usr/bin/env bash
# Staging supervised pipeline — naturalness_blocking ON (프로덕션 전 검증)
#
# Usage:
#   ./staging-supervised-eval.sh [YYYY-MM-DD]
#   HERMES_CRON_SKIP_NOTION=1 ./staging-supervised-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
PASS=0
FAIL=0

record() { [[ "$1" == PASS ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1)); echo "$1 $2"; }

echo "=== Staging Supervised Eval — $STAMP ==="

BLOCKING=$(python3 - <<PY
import os, sys
sys.path.insert(0, "$DIR")
os.environ["HERMES_SUPERVISED_STAGING"] = "1"
from lib.content_quality_config import supervised_stage_blocking
print("1" if supervised_stage_blocking("naturalness") else "0")
PY
)
if [[ "$BLOCKING" == "1" ]]; then
  record PASS "staging_naturalness_blocking"
else
  record FAIL "staging_naturalness_blocking"
fi

PROD_BLOCK=$(python3 - <<PY
import os, sys
sys.path.insert(0, "$DIR")
os.environ.pop("HERMES_SUPERVISED_STAGING", None)
from lib.content_quality_config import supervised_stage_blocking
print("1" if supervised_stage_blocking("naturalness") else "0")
PY
)
if [[ "$PROD_BLOCK" == "1" ]]; then
  record PASS "production_naturalness_blocking"
else
  record FAIL "production_naturalness_blocking"
fi

VOICE_BLOCK=$(python3 - <<PY
import os, sys
sys.path.insert(0, "$DIR")
os.environ.pop("HERMES_SUPERVISED_STAGING", None)
from lib.content_quality_config import supervised_stage_blocking
print("1" if supervised_stage_blocking("voice") else "0")
PY
)
if [[ "$VOICE_BLOCK" == "1" ]]; then
  record PASS "production_voice_blocking"
else
  record FAIL "production_voice_blocking"
fi

export HERMES_SUPERVISED_STAGING=1
export HERMES_CRON_SKIP_NOTION="${HERMES_CRON_SKIP_NOTION:-1}"
OUT=$("$DIR/cron-supervised-pipeline.sh" "$STAMP" 2>&1) || true
echo "$OUT" | tail -20

HANDOFF="$WORKDIR/.harness/handoffs/${STAMP}_supervised-pipeline.json"
STAGE_OK=$(python3 - <<PY
import json, sys
from pathlib import Path
p = Path("$HANDOFF")
if not p.exists():
    print("missing")
    raise SystemExit
d = json.loads(p.read_text(encoding="utf-8"))
for s in d.get("stages", []):
    if s.get("id") == "NATURALNESS":
        print(s.get("status", "?"))
        raise SystemExit
print("no_nat")
PY
)
if [[ "$STAGE_OK" == "PASS" || "$STAGE_OK" == "WARN" ]]; then
  record PASS "staging_naturalness_stage_${STAGE_OK}"
elif [[ "$STAGE_OK" == "FAIL" ]]; then
  record FAIL "staging_naturalness_blocked"
else
  record FAIL "staging_handoff_naturalness"
fi

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
[[ "$FAIL" -eq 0 ]]
