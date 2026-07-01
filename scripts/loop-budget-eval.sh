#!/usr/bin/env bash
# Loop budget kill switch · cap 검증 (결정적)
#
# Usage: ./loop-budget-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
PASS=0
FAIL=0

record() { [[ "$1" == PASS ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1)); echo "$1 $2"; }

echo "=== Loop Budget Eval ==="

RESULT=$(python3 - <<PY
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "$DIR")
from lib.common import studio_today
from lib.content_quality_config import budget_config
from lib.loop_budget import check_loop_budget, read_today_spend, read_today_spend_by_path

errors = []

os.environ["HERMES_LOOP_BUDGET_KILL"] = "1"
st = check_loop_budget()
if st.ok:
    errors.append("kill switch should block")
else:
    print("PASS kill_switch")

del os.environ["HERMES_LOOP_BUDGET_KILL"]

cfg = budget_config()
token_cap = int(cfg.get("daily_token_cap") or 0)
if token_cap <= 0:
    errors.append("daily_token_cap must be set in content-quality.yaml")
else:
    print(f"PASS yaml_daily_token_cap={token_cap}")

with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as tf:
    ledger = Path(tf.name)
    day = studio_today()
    row = {
        "ts": f"{day}T12:00:00Z",
        "path": "test",
        "tokens": token_cap + 1,
        "usd": 0.0,
    }
    tf.write(json.dumps(row) + "\n")

os.environ["HERMES_COST_LEDGER"] = str(ledger)
try:
    st2 = check_loop_budget()
    if st2.ok:
        errors.append("daily token cap should block")
    else:
        print("PASS daily_token_cap")
finally:
    os.environ.pop("HERMES_COST_LEDGER", None)
    ledger.unlink(missing_ok=True)

path_caps = cfg.get("path_daily_token_caps") or {}
humanize_cap = int(path_caps.get("HERMES_HUMANIZE_LLM") or 0)
if humanize_cap <= 0:
    errors.append("path_daily_token_caps.HERMES_HUMANIZE_LLM must be set")
else:
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as tf:
        ledger2 = Path(tf.name)
        day = studio_today()
        tf.write(
            json.dumps(
                {
                    "ts": f"{day}T12:00:00Z",
                    "path": "HERMES_HUMANIZE_LLM",
                    "tokens": humanize_cap + 1,
                    "usd": 0.0,
                }
            )
            + "\n"
        )
    os.environ["HERMES_COST_LEDGER"] = str(ledger2)
    try:
        st3 = check_loop_budget()
        if st3.ok:
            errors.append("path token cap should block")
        elif st3.path != "HERMES_HUMANIZE_LLM":
            errors.append(f"path cap wrong path: {st3.path!r}")
        else:
            print("PASS path_token_cap")
    finally:
        os.environ.pop("HERMES_COST_LEDGER", None)
        ledger2.unlink(missing_ok=True)

# 실제 ledger가 있으면 spend 요약 (blocking 아님)
tokens, usd = read_today_spend()
by_path = read_today_spend_by_path()
if tokens or usd:
    print(f"INFO ledger_today tokens={tokens} usd={usd:.2f} paths={len(by_path)}")

if errors:
    for e in errors:
        print("FAIL", e)
    sys.exit(1)
PY
)

while IFS= read -r line; do
  case "$line" in
    PASS*) record PASS "${line#PASS }" ;;
    FAIL*) record FAIL "${line#FAIL }" ;;
    INFO*) echo "$line" ;;
  esac
done <<< "$RESULT"

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
[[ "$FAIL" -eq 0 ]]
