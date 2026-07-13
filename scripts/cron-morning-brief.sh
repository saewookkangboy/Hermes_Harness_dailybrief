#!/usr/bin/env bash
# 결정적 모닝 브리핑 — hermes cron --no-agent 용 (stdout → Telegram deliver)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
SCRIPTS_DIR="$WORKDIR/scripts"
# shellcheck source=lib/studio-date.sh
source "$SCRIPTS_DIR/lib/studio-date.sh"

DATE="$(studio_commander_date)"
export DATE
SESSION="${TELEGRAM_CHAT_ID:-cron-morning}"

"$SCRIPTS_DIR/hermes-agent.sh" morning --date "$DATE" --session "$SESSION"
