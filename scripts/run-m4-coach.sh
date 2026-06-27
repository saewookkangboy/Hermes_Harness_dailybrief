#!/usr/bin/env bash
# M4 Performance Coach — 전 채널 CTOR·trait 코칭 (결정적)
#
# Usage:
#   ./run-m4-coach.sh [YYYY-MM-DD] [--days 7]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="${1:-$(date +%Y-%m-%d)}"
DAYS=7
[[ "${2:-}" == "--days" && -n "${3:-}" ]] && DAYS="$3"

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
from lib.m4_coach import run_m4_coach, format_coach_summary
r = run_m4_coach('$STAMP', days=$DAYS, write_report=True)
print(format_coach_summary(r))
"
