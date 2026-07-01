#!/usr/bin/env bash
# HERMES_HUMANIZE=1 — 결정적 문체 재정렬 + 선택 LLM humanize-korean
#
# Usage:
#   HERMES_HUMANIZE=1 ./run-humanize-polish.sh [YYYY-MM-DD]
#   HERMES_HUMANIZE=1 HERMES_HUMANIZE_LLM=1 ./run-humanize-polish.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"

if [[ "${HERMES_HUMANIZE:-0}" != "1" ]]; then
  echo "SKIP HERMES_HUMANIZE=0"
  exit 0
fi

USE_LLM=0
[[ "${HERMES_HUMANIZE_LLM:-0}" == "1" ]] && USE_LLM=1

python3 - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.humanize_polish import run_humanize_polish
r = run_humanize_polish("$STAMP", use_llm=$USE_LLM == 1)
print("channels:", ",".join(r.channels) or "(none)")
if r.llm_attempted:
    print("llm: attempted")
for w in r.warnings:
    print("warn:", w)
if not r.channels and r.warnings:
    sys.exit(1)
PY
