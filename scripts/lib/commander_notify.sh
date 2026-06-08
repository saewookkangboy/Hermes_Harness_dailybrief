#!/usr/bin/env bash
# Commander 공용 알림 — Telegram · Slack
# Usage: commander_notify.sh notify "message"
set -euo pipefail

_NOTIFY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

commander_load_chat_id() {
  if [[ -n "${TELEGRAM_CHAT_ID:-}" ]]; then
    echo "$TELEGRAM_CHAT_ID"
    return 0
  fi
  local env_file="${HERMES_ENV:-$HOME/.hermes/.env}"
  if [[ -f "$env_file" ]]; then
    local v
    v=$(grep -E '^TELEGRAM_CHAT_ID=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -n "$v" ]]; then echo "$v"; return 0; fi
    v=$(grep -E '^TELEGRAM_ALLOWED_USERS=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -n "$v" ]]; then echo "$v"; return 0; fi
  fi
  echo ""
}

commander_notify_msg() {
  local msg="$1"
  local chat slack
  chat="$(commander_load_chat_id)"
  # shellcheck source=lib/slack_home.sh
  # shellcheck source=lib/slack_home.sh
  source "$_NOTIFY_DIR/lib/slack_home.sh"
  slack="$(studio_slack_home_channel)"
  [[ -n "$chat" ]] && "$_NOTIFY_DIR/telegram-notify.sh" "$chat" "$msg" 2>/dev/null || true
  [[ -n "$slack" ]] && "$_NOTIFY_DIR/slack-notify.sh" "$slack" "$msg" 2>/dev/null || true
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  case "${1:-notify}" in
    notify)
      shift
      commander_notify_msg "${*:-}"
      ;;
    *)
      commander_notify_msg "${*:-}"
      ;;
  esac
fi
