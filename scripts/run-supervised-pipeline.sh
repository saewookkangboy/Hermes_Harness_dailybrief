#!/usr/bin/env bash
# Pipeline Supervisor — M1→M2→(M2b)→Audit→M5 단계별 감독 (결정적)
#
# Usage:
#   ./run-supervised-pipeline.sh [YYYY-MM-DD]
#   SKIP_NEWSLETTER=1 ./run-supervised-pipeline.sh
#   SKIP_NOTION_ARCHIVE=1 ./run-supervised-pipeline.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="${1:-$(date +%Y-%m-%d)}"
SKIP_NL=0
SKIP_NOTION=0
SKIP_AUDIT=0
[[ "${SKIP_NEWSLETTER:-0}" == "1" ]] && SKIP_NL=1
[[ "${SKIP_NOTION_ARCHIVE:-0}" == "1" ]] && SKIP_NOTION=1
[[ "${SKIP_AUDIT:-0}" == "1" ]] && SKIP_AUDIT=1

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
from lib.pipeline_supervisor import run_supervised_pipeline, format_supervisor_report

def notify(msg):
    print(msg, flush=True)

report = run_supervised_pipeline(
    '$STAMP',
    skip_newsletter=$([[ $SKIP_NL -eq 1 ]] && echo True || echo False),
    skip_notion=$([[ $SKIP_NOTION -eq 1 ]] && echo True || echo False),
    skip_audit=$([[ $SKIP_AUDIT -eq 1 ]] && echo True || echo False),
    notify=notify,
)
print()
print(format_supervisor_report(report))
raise SystemExit(0 if report.success else 1)
"
