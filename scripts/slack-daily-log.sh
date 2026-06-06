#!/usr/bin/env bash
# Hermes Content Studio — 일일 로그·콘텐츠 전문 → Slack
#
# Usage:
#   ./slack-daily-log.sh                    # 오늘 digest 빌드 + Slack 전송
#   ./slack-daily-log.sh 2026-06-06         # 특정 날짜
#   ./slack-daily-log.sh --build-only       # content/logs/*.md 만 저장
#   SLACK_HOME_CHANNEL=C0B8CN2EA05 ./slack-daily-log.sh --send
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
# shellcheck source=lib/slack_home.sh
source "$DIR/lib/slack_home.sh"
export SLACK_HOME_CHANNEL="${SLACK_HOME_CHANNEL:-$(studio_slack_home_channel)}"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

run_python() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

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

# 기본: 빌드 + Slack 전송 (채널 있으면)
if [[ "${ARGS[*]:-}" != *"--build-only"* && "${ARGS[*]:-}" != *"--send"* ]]; then
  ARGS+=(--send)
fi

run_python "$DIR/slack-daily-log.py" "$DATE" "${ARGS[@]}"
