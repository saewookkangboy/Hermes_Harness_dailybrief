#!/usr/bin/env bash
# 런타임 헬스 이상 시에만 stdout 출력 (cron --no-agent: 빈 출력 = 무음)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"

DATE="$(studio_commander_date)"
run_py() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

ISSUES=$(run_py -c "
import sys
sys.path.insert(0, '${DIR}')
from lib.common import studio_today
from lib.runtime_health import run_runtime_checks
issues = run_runtime_checks(studio_today())
print(chr(10).join(issues))
" 2>/dev/null || true)

[[ -n "${ISSUES// }" ]] || exit 0

echo "🚨 Hermes Studio Health · ${DATE}"
echo ""
echo "$ISSUES"
echo ""
echo "복구: ~/hermes-content-studio/scripts/start-services.sh"
