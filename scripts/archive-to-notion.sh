#!/usr/bin/env bash
# Hermes Content Studio — Notion 일자별 아카이브 + Telegram Permalink
# Usage:
#   ./archive-to-notion.sh [YYYY-MM-DD]
#   ./archive-to-notion.sh 2026-06-05 --hygiene-only   # 중복만 Draft Archive 이동
#   ./check-notion-status.sh 2026-06-05 [--fix]
#   ./archive-to-notion.sh 2026-06-05 --telegram-chat 8975802496
#   ./archive-to-notion.sh 2026-06-05 --slack-channel C0B8CN2EA05
#   TELEGRAM_CHAT_ID=8975802496 ./archive-to-notion.sh
#   SLACK_HOME_CHANNEL=C0B8CN2EA05 ./archive-to-notion.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

ARGS=()
DATE=""
for arg in "$@"; do
  case "$arg" in
    --*) ARGS+=("$arg") ;;
    *)
      if [[ -z "$DATE" ]]; then DATE="$arg"; else ARGS+=("$arg"); fi
      ;;
  esac
done
DATE="${DATE:-$(studio_today)}"

if [[ -n "${TELEGRAM_CHAT_ID:-}" && "${ARGS[*]:-}" != *"--telegram-chat"* ]]; then
  ARGS+=(--telegram-chat "$TELEGRAM_CHAT_ID")
fi

if [[ -n "${SLACK_HOME_CHANNEL:-}" && "${ARGS[*]:-}" != *"--slack-channel"* ]]; then
  ARGS+=(--slack-channel "$SLACK_HOME_CHANNEL")
fi

echo "[Notion Archive] 시작: $DATE" | tee -a ~/.hermes/logs/content-studio.log

run_archive() {
  if [[ ${#ARGS[@]} -gt 0 ]]; then
if [[ -x "$HERMES_PY" ]]; then
  "$HERMES_PY" "$DIR/archive-to-notion.py" "$DATE" --json "${ARGS[@]}"
else
  python3 "$DIR/archive-to-notion.py" "$DATE" --json "${ARGS[@]}"
fi

# Slack: archive가 --notify-final 이면 요약만 전송됨. full 모드일 때만 digest 옵션.
if [[ -n "${SLACK_HOME_CHANNEL:-}" && "${ARGS[*]:-}" != *"--no-notify"* && "${ARGS[*]:-}" != *"--notify-final"* ]]; then
  SKIP_INIT=1 "$DIR/slack-daily-log.sh" "$DATE" --send --summary-only 2>>"$HOME/.hermes/logs/content-studio.log" || true
fi
  else
    if [[ -x "$HERMES_PY" ]]; then
      "$HERMES_PY" "$DIR/archive-to-notion.py" "$DATE" --json
    else
      python3 "$DIR/archive-to-notion.py" "$DATE" --json
    fi
  fi
}
run_archive
