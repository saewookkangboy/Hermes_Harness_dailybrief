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
# shellcheck source=lib/telegram_sync_guard.sh
source "$DIR/lib/telegram_sync_guard.sh"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
ARCHIVE_LOCK="$WORKDIR/.harness/archive-notion.lock"

ARGS=()
REQUESTED_DATE=""
for arg in "$@"; do
  case "$arg" in
    --*) ARGS+=("$arg") ;;
    *)
      if [[ -z "$REQUESTED_DATE" ]]; then REQUESTED_DATE="$arg"; else ARGS+=("$arg"); fi
      ;;
  esac
done
DATE="${REQUESTED_DATE:-$(studio_commander_date)}"

if [[ -n "${TELEGRAM_CHAT_ID:-}" && "${ARGS[*]:-}" != *"--telegram-chat"* ]]; then
  ARGS+=(--telegram-chat "$TELEGRAM_CHAT_ID")
fi

if [[ -n "${SLACK_HOME_CHANNEL:-}" && "${ARGS[*]:-}" != *"--slack-channel"* ]]; then
  ARGS+=(--slack-channel "$SLACK_HOME_CHANNEL")
fi

# Telegram/최종 알림 경로: commander SoT 날짜만 허용 (stale DATE env·과거 아카이브 차단)
COMMANDER_DATE="$(studio_commander_date)"
HAS_NOTIFY_FINAL=0
for a in "${ARGS[@]:-}"; do
  [[ "$a" == "--notify-final" ]] && HAS_NOTIFY_FINAL=1
done
if [[ -n "${TELEGRAM_CHAT_ID:-}" || "$HAS_NOTIFY_FINAL" -eq 1 ]]; then
  if [[ "$DATE" != "$COMMANDER_DATE" ]]; then
    echo "⚠️  Notion sync 날짜 보정: ${DATE} → ${COMMANDER_DATE} (commander SoT)" \
      | tee -a ~/.hermes/logs/content-studio.log >&2
    DATE="$COMMANDER_DATE"
  fi
fi

mkdir -p "$WORKDIR/.harness"
if command -v flock >/dev/null 2>&1; then
  exec 200>"$ARCHIVE_LOCK"
  if ! flock -n 200; then
    echo "ℹ️  Notion archive 이미 실행 중 — skip ($DATE)" | tee -a ~/.hermes/logs/content-studio.log >&2
    exit 0
  fi
else
  if [[ -f "$ARCHIVE_LOCK" ]]; then
    old_pid=$(cat "$ARCHIVE_LOCK" 2>/dev/null || echo "")
    if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
      echo "ℹ️  Notion archive 이미 실행 중 (PID $old_pid) — skip ($DATE)" \
        | tee -a ~/.hermes/logs/content-studio.log >&2
      exit 0
    fi
  fi
  echo $$ > "$ARCHIVE_LOCK"
  trap 'rm -f "$ARCHIVE_LOCK"' EXIT
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
