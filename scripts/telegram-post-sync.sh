#!/usr/bin/env bash
# Telegram 요청 완료 후 Notion 동기화 + Permalink 전송
# watch-telegram.sh 또는 Hermes 에이전트가 호출
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
DATE="${1:-$(studio_today)}"
CHAT_ID="${2:-${TELEGRAM_CHAT_ID:-}}"

if [[ -z "$CHAT_ID" ]]; then
  echo "telegram-post-sync: TELEGRAM_CHAT_ID 없음" >&2
  exit 0
fi

export TELEGRAM_CHAT_ID="$CHAT_ID"
"$DIR/archive-to-notion.sh" "$DATE" --telegram-chat "$CHAT_ID" --notify-final || true
