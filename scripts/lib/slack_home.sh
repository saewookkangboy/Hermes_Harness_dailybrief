#!/usr/bin/env bash
# Slack home channel resolver — env → ~/.hermes/.env → config default (#일반데이터)

studio_slack_home_channel() {
  if [[ -n "${SLACK_HOME_CHANNEL:-}" ]]; then
    echo "$SLACK_HOME_CHANNEL"
    return 0
  fi
  local env_file="${HERMES_ENV:-$HOME/.hermes/.env}"
  if [[ -f "$env_file" ]]; then
    local v
    v=$(grep -E '^SLACK_HOME_CHANNEL=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -n "$v" ]]; then
      echo "$v"
      return 0
    fi
  fi
  # slack-routing.yaml default — #일반데이터 (troeteam)
  echo "C0B8CN2EA05"
}

studio_slack_home_channel_name() {
  if [[ -n "${SLACK_HOME_CHANNEL_NAME:-}" ]]; then
    echo "$SLACK_HOME_CHANNEL_NAME"
    return 0
  fi
  local env_file="${HERMES_ENV:-$HOME/.hermes/.env}"
  if [[ -f "$env_file" ]]; then
    local v
    v=$(grep -E '^SLACK_HOME_CHANNEL_NAME=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -n "$v" ]]; then
      echo "$v"
      return 0
    fi
  fi
  echo "일반데이터"
}
