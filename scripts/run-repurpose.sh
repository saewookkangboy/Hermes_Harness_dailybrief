#!/usr/bin/env bash
# Repurpose Agent — Brief 인사이트 1건 → 채널 재조립 (결정적)
#
# Usage:
#   ./run-repurpose.sh [YYYY-MM-DD] CHANNEL [INSIGHT_INDEX] [--validate]
#   ./run-repurpose.sh 2026-06-26 linkedin 3 --validate
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="${1:-$(date +%Y-%m-%d)}"
CHANNEL="${2:-linkedin}"
INDEX="${3:-1}"
VALIDATE=0
[[ "${4:-}" == "--validate" ]] && VALIDATE=1
[[ "$INDEX" == "--validate" ]] && { INDEX=1; VALIDATE=1; }

PY_VALIDATE=False
[[ "$VALIDATE" -eq 1 ]] && PY_VALIDATE=True

run_py() {
  if [[ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]]; then
    "$HOME/.hermes/hermes-agent/venv/bin/python" "$@"
  else
    python3 "$@"
  fi
}

run_py -c "
import sys
sys.path.insert(0, '$DIR')
from lib.repurpose_pipeline import run_repurpose, format_repurpose_summary
r = run_repurpose('$STAMP', '$CHANNEL', int('$INDEX'), validate=$PY_VALIDATE)
print(format_repurpose_summary(r))
"
