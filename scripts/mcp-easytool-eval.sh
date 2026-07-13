#!/usr/bin/env bash
# EasyTool-style commander prompt 검증 (결정적)
#
# Usage: ./mcp-easytool-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
PASS=0
FAIL=0

record() { [[ "$1" == PASS ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1)); echo "$1 $2"; }

echo "=== MCP EasyTool Eval ==="

RESULT=$(python3 - <<PY
import sys
from pathlib import Path

sys.path.insert(0, "$DIR")
from lib.easytool_prompt import (
    build_compact_channel_prompt,
    compact_prompt_chars,
    validate_easytool,
    verbose_prompt_chars,
)

errors = []

ok, errs = validate_easytool()
if ok:
    print("PASS easytool_validate")
else:
    errors.extend(errs)

compact = build_compact_channel_prompt()
verbose = verbose_prompt_chars()
if verbose > 0:
    ratio = round(100 * (verbose - len(compact)) / verbose)
    print(f"PASS prompt_savings verbose={verbose} compact={len(compact)} (-{ratio}%)")
    if len(compact) >= verbose:
        errors.append("compact not shorter than verbose")
else:
    print(f"PASS compact_chars={len(compact)}")

# quick_commands coverage (telegram-routing.yaml)
import yaml
routing = yaml.safe_load(Path("$WORKDIR/config/telegram-routing.yaml").read_text(encoding="utf-8"))
qc = routing.get("quick_commands") or {}
hints_path = Path("$WORKDIR/config/commander-easytool.yaml")
hints_cfg = yaml.safe_load(hints_path.read_text(encoding="utf-8")).get("easytool") or {}
hints = hints_cfg.get("quick_command_hints") or {}
core = ["pipeline", "research", "content", "newsletter", "sync"]
missing_qc = [k for k in core if k not in qc]
missing_hints = [k for k in core if k not in hints]
if missing_qc:
    errors.append("quick_commands missing: " + ",".join(missing_qc))
else:
    print("PASS quick_commands_core")
if missing_hints:
    errors.append("hints missing: " + ",".join(missing_hints))
else:
    print("PASS easytool_hints_core")

if errors:
    for e in errors:
        print(f"FAIL {e}", file=sys.stderr)
    raise SystemExit(1)
PY
)

while IFS= read -r line; do
  case "$line" in
    PASS*) record PASS "${line#PASS }" ;;
    FAIL*) record FAIL "${line#FAIL }" ;;
  esac
done <<< "$RESULT"

# setup-telegram-routing wiring (dry — no gateway restart)
if grep -q "easytool_prompt" "$DIR/setup-telegram-routing.sh"; then
  record PASS "setup_telegram_easytool_wiring"
else
  record FAIL "setup_telegram_easytool_wiring"
fi

echo ""
echo "=== Summary: $PASS pass, $FAIL fail ==="
[[ "$FAIL" -eq 0 ]]
