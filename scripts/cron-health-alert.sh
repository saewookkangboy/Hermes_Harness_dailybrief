#!/usr/bin/env bash
# 런타임 헬스 이상 시에만 stdout 출력 (cron --no-agent: 빈 출력 = 무음)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
# shellcheck source=lib/watch_telegram_singleton.sh
source "$DIR/lib/watch_telegram_singleton.sh"

DATE="$(studio_commander_date)"

ensure_watch_telegram() {
  local ensure_lock="${HERMES_WATCH_ENSURE_LOCK:-$HOME/hermes-content-studio/.harness/watch-telegram-ensure.lock.d}"
  if ! mkdir "$ensure_lock" 2>/dev/null; then
    return 0
  fi
  trap 'rmdir "$ensure_lock" 2>/dev/null || true' RETURN

  local n
  n=$(watch_telegram_root_count)
  if (( n > 1 )); then
    SKIP_INIT=1 "$DIR/kill-stale-watch-telegram.sh" 2>/dev/null || true
    sleep 0.5
    n=0
  fi
  if (( n == 1 )); then
    return 0
  fi
  mkdir -p "$HOME/.hermes/logs"
  nohup "$DIR/watch-telegram.sh" >>"$HOME/.hermes/logs/watch-telegram.log" 2>&1 &
  echo $! > /tmp/hermes-watch-telegram.pid
  sleep 0.5
}

ensure_watch_telegram

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
