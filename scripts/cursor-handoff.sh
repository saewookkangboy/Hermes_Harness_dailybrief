#!/usr/bin/env bash
# Hermes Content Studio — Slack /cursor → Cursor HANDOFF
#
# Telegram /automate 와 동일한 Codex HANDOFF 경로를 재사용하고,
# Slack 알림을 켠 뒤 Cursor CLI를 실행합니다.
#
# Usage:
#   cursor-handoff.sh qc "<구현 설명>"
#   cursor-handoff.sh auto "<구현 설명>"
#   cursor-handoff.sh automate "<구현 설명>"
#
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"

export HERMES_NOTIFY_SLACK=1
if [[ -z "${SLACK_HOME_CHANNEL:-}" && -f "$HOME/.hermes/.env" ]]; then
  SLACK_HOME_CHANNEL=$(grep -E '^SLACK_HOME_CHANNEL=' "$HOME/.hermes/.env" 2>/dev/null \
    | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
  export SLACK_HOME_CHANNEL
fi
if [[ -z "${SLACK_HOME_CHANNEL:-}" ]]; then
  export SLACK_HOME_CHANNEL=C0B8CN2EA05
fi

usage() {
  cat <<'EOF'
Usage: cursor-handoff.sh {qc|auto|automate} <message>

Slack /cursor — Codex vibe-coding HANDOFF 생성 후 run-cursor-handoff --background
(HERMES_CURSOR_AUTO=0 이면 CLI 생략)

Examples:
  cursor-handoff.sh qc "콘텐츠 패키지에 threads 채널 validate 추가"
  HERMES_CURSOR_AUTO=0 cursor-handoff.sh automate "HANDOFF만 생성"
EOF
}

MODE="${1:-}"
shift || true
MSG="${*:-}"

case "$MODE" in
  -h|--help|help|"")
    usage
    [[ -n "$MODE" ]] || exit 1
    exit 0
    ;;
  qc|auto|automate)
    if [[ -z "$MSG" ]]; then
      echo "❌ message required" >&2
      usage >&2
      exit 1
    fi
    # `auto` = 커맨더가 자연어에서 추론한 요청 → HANDOFF만 (Cursor 자동 실행 없음).
    # qc(/cursor 슬래시)·automate(명시 호출)·"/cursor …" 메시지는 기존대로 Cursor까지.
    if [[ "$MODE" == "auto" && ! "$MSG" =~ ^[[:space:]]*/(automate|cursor)([[:space:]]|$) ]]; then
      export HERMES_CURSOR_AUTO=0
      echo "ℹ️ 자연어 요청으로 판단해 HANDOFF만 만들어요. Cursor 실행은 /cursor 로 요청해 주세요."
    fi
    # telegram-custom: `automate <prompt>` submits Codex+vibe-coding-cursor job
    exec "$DIR/telegram-custom.sh" automate "$MSG"
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    usage >&2
    exit 1
    ;;
esac
