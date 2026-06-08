#!/usr/bin/env bash
# Commander 공용 알림 — Telegram · Slack
# shellcheck shell=bash

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

commander_notify() {
  local msg="$1"
  local scripts="${HERMES_SCRIPTS:-$HOME/hermes-content-studio/scripts}"
  local chat slack
  chat="$(commander_load_chat_id)"
  # shellcheck source=lib/slack_home.sh
  source "$scripts/lib/slack_home.sh"
  slack="$(studio_slack_home_channel)"
  [[ -n "$chat" ]] && "$scripts/telegram-notify.sh" "$chat" "$msg" 2>/dev/null || true
  [[ -n "$slack" ]] && "$scripts/slack-notify.sh" "$slack" "$msg" 2>/dev/null || true
}
