#!/usr/bin/env bash
# Notion OAuth 지속 감시 — 2h cron · 선제 refresh · Telegram 알림 (이상 시만)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
# shellcheck source=lib/cron_bootstrap.sh
source "$WORKDIR/scripts/lib/cron_bootstrap.sh"
# shellcheck source=lib/studio-date.sh
source "$SCRIPTS_DIR/lib/studio-date.sh"

DATE="$(studio_commander_date)"

OUT=$(cron_run_py -c "
import sys
sys.path.insert(0, '${SCRIPTS_DIR}')
from lib.notion_oauth_watch import run_notion_oauth_watch
result = run_notion_oauth_watch(record_state=True)
if result.should_alert:
    print(result.message)
elif result.severity == 'ok':
    print('OK', result.status.detail, sep='|')
" 2>/dev/null || true)

[[ -n "${OUT// }" ]] || exit 0

if [[ "$OUT" == OK\|* ]]; then
  exit 0
fi

echo "🔐 Notion OAuth Watch · ${DATE}"
echo ""
echo "$OUT"
