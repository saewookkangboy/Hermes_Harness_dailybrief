#!/usr/bin/env bash
# SLACK_HOME_CHANNEL / NAME만 .env에 기록 (토큰 없이 digest·라우팅용)
set -euo pipefail

ENV_FILE="${HERMES_ENV:-$HOME/.hermes/.env}"
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/slack_home.sh
source "$DIR/lib/slack_home.sh"

CHANNEL="${SLACK_HOME_CHANNEL:-$(studio_slack_home_channel)}"
NAME="${SLACK_HOME_CHANNEL_NAME:-$(studio_slack_home_channel_name)}"

touch "$ENV_FILE"
update_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  elif grep -q "^# ${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^# ${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

update_env "SLACK_HOME_CHANNEL" "$CHANNEL"
update_env "SLACK_HOME_CHANNEL_NAME" "$NAME"
rm -f "${ENV_FILE}.bak"

echo "✅ SLACK_HOME_CHANNEL=${CHANNEL} (#${NAME})"
