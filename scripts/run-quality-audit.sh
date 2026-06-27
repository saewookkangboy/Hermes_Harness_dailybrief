#!/usr/bin/env bash
# Quality Auditor Agent — 결정적 DoD·채널 검증 일괄 감사
#
# Usage:
#   ./run-quality-audit.sh [YYYY-MM-DD]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="${1:-$(date +%Y-%m-%d)}"

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
from lib.quality_auditor import audit_stamp, format_audit_summary
report = audit_stamp('$STAMP', write_report=True)
print(format_audit_summary(report))
raise SystemExit(0 if report.all_pass else 1)
"
