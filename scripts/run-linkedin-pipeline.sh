#!/usr/bin/env bash
# LinkedIn M3 sub-pipeline — analyze → strategy → draft (결정적)
#
# Usage:
#   ./run-linkedin-pipeline.sh [YYYY-MM-DD]
#   ./run-linkedin-pipeline.sh 2026-06-07 --validate
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="${1:-$(date +%Y-%m-%d)}"
VALIDATE=0
[[ "${2:-}" == "--validate" ]] && VALIDATE=1

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
from lib.linkedin_pipeline import run_linkedin_pipeline, format_pipeline_summary
r = run_linkedin_pipeline('$STAMP', validate=$PY_VALIDATE)
print(format_pipeline_summary(r))
"
