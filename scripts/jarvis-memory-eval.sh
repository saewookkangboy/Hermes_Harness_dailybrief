#!/usr/bin/env bash
# JARVIS.md + OMM 메모리 wiring 검증 (결정적)
#
# Usage: ./jarvis-memory-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
PASS=0
FAIL=0

record() { [[ "$1" == PASS ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1)); echo "$1 $2"; }

echo "=== JARVIS Memory Eval ==="

RESULT=$(python3 - <<PY
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "$DIR")
from lib.omm import (
    JARVIS_PATH,
    OMM_PATH,
    format_omm_block,
    read_omm,
    record_omm,
    validate_jarvis_md,
)
from lib.session_handoff import build_handoff_markdown

errors = []

ok, errs = validate_jarvis_md()
if ok:
    print("PASS jarvis_md_sections")
else:
    errors.extend(errs)

if not JARVIS_PATH.exists():
    errors.append("JARVIS.md missing")
else:
    print("PASS jarvis_md_exists")

# OMM round-trip (temp ledger)
orig = OMM_PATH.read_text(encoding="utf-8") if OMM_PATH.exists() else ""
try:
    if OMM_PATH.exists():
        OMM_PATH.unlink()
    entry = record_omm("eval test mistake", "eval test defense", context="jarvis-memory-eval")
    rows = read_omm(5)
    if not rows or rows[-1].get("mistake") != "eval test mistake":
        errors.append("omm record/read failed")
    else:
        print("PASS omm_record_read")
    block = format_omm_block(3)
    if "eval test mistake" not in block:
        errors.append("format_omm_block missing entry")
    else:
        print("PASS omm_format_block")
finally:
    if OMM_PATH.exists():
        OMM_PATH.unlink()
    if orig:
        OMM_PATH.write_text(orig, encoding="utf-8")

md = build_handoff_markdown("jarvis-eval", m4_days=1)
if "## OMM (실수 방어선)" not in md:
    errors.append("session_handoff missing OMM section")
else:
    print("PASS session_handoff_omm")

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

echo ""
echo "=== Summary: $PASS pass, $FAIL fail ==="
[[ "$FAIL" -eq 0 ]]
