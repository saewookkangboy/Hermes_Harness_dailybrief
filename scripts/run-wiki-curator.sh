#!/usr/bin/env bash
# Wiki Curator — seed · lint · ingest 큐 (결정적)
#
# Usage:
#   ./run-wiki-curator.sh [status|seed|lint|ingest|all]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-status}"

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
from lib.wiki_curator import run_wiki_curator, format_curator_summary
r = run_wiki_curator('$MODE', write_report=True)
print(format_curator_summary(r))
if '$MODE' in ('seed', 'all') and r.get('seed', {}).get('concepts', 0) == 0:
    raise SystemExit(1)
"
