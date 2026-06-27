#!/usr/bin/env bash
# Blog M3 sub-pipeline — seo → structure → validate (결정적)
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
from lib.blog_pipeline import run_blog_pipeline, format_pipeline_summary
r = run_blog_pipeline('$STAMP', validate=$PY_VALIDATE)
print(format_pipeline_summary(r))
"
