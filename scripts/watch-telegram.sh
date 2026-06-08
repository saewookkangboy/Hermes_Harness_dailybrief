#!/usr/bin/env bash
# Hermes Content Studio — Telegram 요청 진행 상황 모니터 + Notion 동기화
#
# Telegram 봇 요청 시:
#   1) 단계별 Telegram 진행 메시지
#   2) 에이전트 완료 후 Notion 100% 동기화 + Permalink 전송
#
# Usage:
#   ./watch-telegram.sh          # 실시간 모니터 (Ctrl+C 종료)
#   ./watch-telegram.sh --once   # 최근 Telegram 이벤트만 출력
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
SCRIPTS="$WORKDIR/scripts"
AGENT_LOG="${HERMES_AGENT_LOG:-$HOME/.hermes/logs/agent.log}"
GATEWAY_LOG="${HERMES_GATEWAY_LOG:-$HOME/.hermes/logs/gateway.log}"
STUDIO_LOG="${HERMES_STUDIO_LOG:-$HOME/.hermes/logs/content-studio.log}"
STATE_DIR="${HERMES_WATCH_STATE:-$WORKDIR/.harness/watch-telegram-state/$$}"
INSTANCE_LOCK="${HERMES_WATCH_LOCK:-$WORKDIR/.harness/watch-telegram.lock}"
SYNC_DEBOUNCE_SEC="${NOTION_SYNC_DEBOUNCE_SEC:-0}"
BAR_WIDTH=24
MODE="${1:-follow}"
# shellcheck source=lib/studio-date.sh
source "$SCRIPTS/lib/studio-date.sh"
# shellcheck source=lib/telegram_sync_guard.sh
source "$SCRIPTS/lib/telegram_sync_guard.sh"

if [[ "$MODE" != "--once" ]]; then
  if [[ -f "$INSTANCE_LOCK" ]]; then
    old_pid=$(cat "$INSTANCE_LOCK" 2>/dev/null || echo "")
    if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
      echo "⚠️  watch-telegram 이미 실행 중 (PID $old_pid). 중복 실행 시 Notion sync가 2번 됩니다." >&2
      echo "   종료: kill $old_pid" >&2
      exit 1
    fi
  fi
  echo $$ > "$INSTANCE_LOCK"
fi

mkdir -p "$STATE_DIR"
PHASE_FILE="$STATE_DIR/phase"
ACTIVE_FILE="$STATE_DIR/active"
START_FILE="$STATE_DIR/start"
MSG_FILE="$STATE_DIR/last_msg"
SESSION_FILE="$STATE_DIR/session"
CHAT_FILE="$STATE_DIR/chat_id"
NOTIFIED_FILE="$STATE_DIR/last_notified_phase"
SYNC_LOCK="$STATE_DIR/sync_lock"
LAST_SYNC_FILE="$STATE_DIR/last_sync_ts"
LAST_EVENT_FILE="$STATE_DIR/last_event_hash"
SYNC_RUNNING="$STATE_DIR/sync_running"
SLASH_FILE="$STATE_DIR/slash_cmd"

echo "phase=대기 중" > "$PHASE_FILE"
echo "0" > "$ACTIVE_FILE"
echo "0" > "$START_FILE"
echo "" > "$MSG_FILE"
echo "" > "$SESSION_FILE"
echo "" > "$CHAT_FILE"
echo "" > "$NOTIFIED_FILE"
touch "$SYNC_LOCK"

cleanup() {
  [[ -n "${TAIL_PID:-}" ]] && kill "$TAIL_PID" 2>/dev/null || true
  [[ -n "${BAR_PID:-}" ]] && kill "$BAR_PID" 2>/dev/null || true
  rm -rf "$STATE_DIR"
  [[ -f "$INSTANCE_LOCK" ]] && [[ "$(cat "$INSTANCE_LOCK" 2>/dev/null)" == "$$" ]] && rm -f "$INSTANCE_LOCK"
}
trap cleanup EXIT INT TERM

notify_telegram() {
  local chat="$1"
  local msg="$2"
  [[ -z "$chat" ]] && return 0
  [[ "${TELEGRAM_PROGRESS:-1}" == "0" ]] && return 0
  local dated
  dated="$(studio_commander_date)
${msg}"
  local last
  last=$(cat "$NOTIFIED_FILE" 2>/dev/null || echo "")
  [[ "$last" == "$dated" ]] && return 0
  echo "$dated" > "$NOTIFIED_FILE"
  "$SCRIPTS/telegram-notify.sh" "$chat" "$dated" 2>/dev/null || true
}

render_bar() {
  local elapsed="$1"
  local phase="$2"
  local ollama_cpu="${3:-0}"
  local filled=$(( elapsed % (BAR_WIDTH + 1) ))
  local bar=""
  local i
  for ((i=0; i<BAR_WIDTH; i++)); do
    if (( i < filled )); then bar+="█"; else bar+="░"; fi
  done
  local mins=$(( elapsed / 60 ))
  local secs=$(( elapsed % 60 ))
  printf '\r\033[K[%s] %02d:%02d | %s | Ollama %s%%' "$bar" "$mins" "$secs" "$phase" "$ollama_cpu" >&2
}

get_ollama_cpu() {
  ps aux 2>/dev/null | rg "llama-server" | rg -v rg | awk '{print int($3)}' | head -1 || echo "0"
}

print_event() {
  local ts="$1"
  local label="$2"
  local detail="$3"
  printf '\n\033[36m%s\033[0m \033[1m%s\033[0m %s\n' "$ts" "$label" "$detail"
}

extract_msg() {
  sed -n "s/.*msg='\([^']*\)'.*/\1/p"
}

extract_session() {
  sed -n 's/.*session=\([^ ]*\).*/\1/p'
}

extract_chat() {
  sed -n 's/.*chat=\([0-9]*\).*/\1/p'
}

extract_response_chat() {
  sed -n 's/.*Sending response ([0-9]* chars) to \([0-9]*\).*/\1/p'
}

event_seen() {
  local line="$1"
  local hash last
  hash=$(printf '%s' "$line" | shasum -a 256 2>/dev/null | awk '{print $1}' || printf '%s' "$line" | md5 -q 2>/dev/null || echo "$line")
  last=$(cat "$LAST_EVENT_FILE" 2>/dev/null || echo "")
  [[ "$last" == "$hash" ]] && return 0
  echo "$hash" > "$LAST_EVENT_FILE"
  return 1
}

sync_debounce_ok() {
  local now last
  now=$(date +%s)
  last=$(cat "$LAST_SYNC_FILE" 2>/dev/null || echo 0)
  (( now - last >= SYNC_DEBOUNCE_SEC ))
}

run_post_sync() {
  # 기본 OFF — 슬래시/파이프라인이 Notion sync 담당. 대화형 LLM만 HERMES_WATCH_POST_SYNC=1
  [[ "${HERMES_WATCH_POST_SYNC:-0}" == "1" ]] || return 0
  local chat sync_date
  chat=$(cat "$CHAT_FILE" 2>/dev/null || echo "")
  [[ -z "$chat" ]] && return 0
  if [[ -f "$SLASH_FILE" ]]; then
    echo "ℹ️  슬래시 커맨드 — 파이프라인 sync가 알림 담당 (watch skip)" >&2
    rm -f "$SLASH_FILE"
    return 0
  fi
  if telegram_sync_should_skip_watch; then
    return 0
  fi
  if [[ -f "$SYNC_RUNNING" ]]; then
    echo "ℹ️  Notion sync 이미 실행 중 — skip" >&2
    return 0
  fi
  sync_date="$(studio_commander_date)"
  notify_telegram "$chat" "[████░] 4/5 Notion 동기화 중… ($sync_date)"
  (
    touch "$SYNC_RUNNING"
    "$SCRIPTS/telegram-post-sync.sh" "$sync_date" "$chat" || true
    rm -f "$SYNC_RUNNING"
  ) &
  date +%s > "$LAST_SYNC_FILE"
}

handle_line() {
  local line="$1"
  local ts phase detail session msg chat

  # gateway.log 전용 이벤트는 agent.log 중복 처리 방지
  if echo "$line" | grep -q "\[Telegram\] Sending response"; then
    if ! echo "$line" | grep -q "gateway.platforms"; then
      return 0
    fi
  fi
  event_seen "$line" && return 0

  ts=$(echo "$line" | awk '{print $1, $2}' | sed 's/,//')
  chat=$(echo "$line" | extract_chat)

  if echo "$line" | grep -q "inbound message: platform=telegram"; then
    msg=$(echo "$line" | extract_msg)
    if echo "${msg:-}" | grep -qE '^/[a-zA-Z0-9_-]+'; then
      echo "1" > "$SLASH_FILE"
    else
      rm -f "$SLASH_FILE"
    fi
    [[ -n "$chat" ]] && echo "$chat" > "$CHAT_FILE"
    echo "$msg" > "$MSG_FILE"
    echo "1" > "$ACTIVE_FILE"
    date +%s > "$START_FILE"
    echo "" > "$NOTIFIED_FILE"
    touch "$SYNC_LOCK"
    echo "요청 수신" > "$PHASE_FILE"
    print_event "$ts" "[Telegram]" "요청: ${msg:-?}"
    notify_telegram "$chat" "[█░░░░] 1/5 요청 수신
${msg:-작업 요청}"
    return
  fi

  if echo "$line" | grep -q "conversation turn:" && echo "$line" | grep -q "platform=telegram"; then
    session=$(echo "$line" | extract_session)
    msg=$(echo "$line" | sed -n "s/.*msg='\([^']*\)'.*/\1/p")
    [[ -n "$session" ]] && echo "$session" > "$SESSION_FILE"
    echo "에이전트 시작" > "$PHASE_FILE"
    print_event "$ts" "[Agent]" "세션 ${session:-?} — ${msg:-작업 시작}"
    chat=$(cat "$CHAT_FILE" 2>/dev/null || echo "$chat")
    notify_telegram "$chat" "[██░░░] 2/5 에이전트 처리 중
콘텐츠 생성·리서치 진행"
    return
  fi

  if echo "$line" | grep -qiE "web_search|ddgs"; then
    echo "웹 검색" > "$PHASE_FILE"
    print_event "$ts" "[Tool]" "web_search"
    chat=$(cat "$CHAT_FILE" 2>/dev/null || echo "")
    notify_telegram "$chat" "[███░░] 3/5 웹 리서치 수집"
    return
  fi

  if echo "$line" | grep -qiE "write_file|patch_file|read_file"; then
    local tool
    tool=$(echo "$line" | rg -oi "write_file|patch_file|read_file" | head -1 || echo "file")
    echo "파일 작업" > "$PHASE_FILE"
    print_event "$ts" "[Tool]" "$tool"
    if echo "$line" | grep -qi "content/"; then
      chat=$(cat "$CHAT_FILE" 2>/dev/null || echo "")
      notify_telegram "$chat" "[███░░] 3/5 콘텐츠 파일 저장 중"
    fi
    return
  fi

  if echo "$line" | grep -q "chat_completion_stream_request"; then
    echo "LLM 추론" > "$PHASE_FILE"
    return
  fi

  if echo "$line" | grep -q "stream_request_complete"; then
    echo "LLM 턴 완료" > "$PHASE_FILE"
    return
  fi

  if echo "$line" | grep -q "\[Telegram\] Sending response"; then
    detail=$(echo "$line" | sed -n 's/.*Sending response (\([^)]*\)).*/\1/p')
    chat=$(echo "$line" | extract_response_chat)
    [[ -n "$chat" ]] && echo "$chat" > "$CHAT_FILE"
    echo "0" > "$ACTIVE_FILE"
    echo "Notion 동기화" > "$PHASE_FILE"
    print_event "$ts" "[Telegram]" "응답 전송 완료 (${detail:-ok}) — Notion 동기화 시작"
    chat=$(cat "$CHAT_FILE" 2>/dev/null || echo "$chat")
    notify_telegram "$chat" "[████░] 4/5 Hermes 응답 완료 → Notion 동기화"
    run_post_sync
    return
  fi

  if echo "$line" | grep -q "\[Notion Archive\]"; then
    detail=$(echo "$line" | sed 's/.*\[Notion Archive\] //')
    echo "Notion 아카이브" > "$PHASE_FILE"
    print_event "$ts" "[Notion]" "$detail"
    return
  fi

  if echo "$line" | grep -qiE "ERROR|WARNING" && echo "$line" | grep -qiE "telegram|run_agent|tools\.|\[Notion"; then
    detail=$(echo "$line" | sed 's/^[^ ]* [^ ]* //')
    print_event "$ts" "[Warn]" "$detail"
    return
  fi
}

status_loop() {
  while true; do
    local active phase start now elapsed cpu
    active=$(cat "$ACTIVE_FILE" 2>/dev/null || echo 0)
    phase=$(cat "$PHASE_FILE" 2>/dev/null || echo "대기 중")
    start=$(cat "$START_FILE" 2>/dev/null || echo 0)
    cpu=$(get_ollama_cpu)

    if [[ "$active" == "1" && "$start" -gt 0 ]]; then
      now=$(date +%s)
      elapsed=$(( now - start ))
      if [[ "$phase" == "대기 중" || "$phase" == "요청 수신" ]]; then
        if pgrep -f "llama-server" >/dev/null 2>&1 && [[ "$cpu" -gt 5 ]]; then
          phase="LLM 추론"
          echo "$phase" > "$PHASE_FILE"
        fi
      fi
      render_bar "$elapsed" "$phase" "$cpu" >&2
    else
      render_bar 0 "대기 중 (Telegram 요청 대기)" "$cpu" >&2
    fi
    sleep 2
  done
}

if [[ "$MODE" == "--once" ]]; then
  rg "platform=telegram|\[Telegram\]" "$GATEWAY_LOG" "$AGENT_LOG" 2>/dev/null | tail -20
  exit 0
fi

for f in "$GATEWAY_LOG" "$AGENT_LOG"; do
  [[ -f "$f" ]] || { echo "로그 없음: $f" >&2; exit 1; }
done
touch "$STUDIO_LOG" 2>/dev/null || true
chmod +x "$SCRIPTS/telegram-notify.sh" "$SCRIPTS/telegram-post-sync.sh" 2>/dev/null || true

if ! pgrep -f "hermes_cli.main gateway" >/dev/null 2>&1; then
  echo "⚠️  Gateway 미실행 — Telegram 요청은 처리되지 않습니다." >&2
  echo "   hermes gateway restart" >&2
fi

echo "=== Telegram 요청 모니터 (Notion Permalink 자동 전송) ===" >&2
echo "로그: $GATEWAY_LOG" >&2
echo "      $AGENT_LOG" >&2
echo "      $STUDIO_LOG (Notion archive)" >&2
echo "Telegram에서 요청 → 단계별 알림 + Notion Permalink. (Ctrl+C 종료)" >&2
echo "" >&2

status_loop &
BAR_PID=$!

tail -F "$GATEWAY_LOG" "$AGENT_LOG" "$STUDIO_LOG" 2>/dev/null | while IFS= read -r line; do
  case "$line" in
    "==> "*|"")
      continue
      ;;
  esac
  handle_line "$line"
done &
TAIL_PID=$!

wait "$TAIL_PID" 2>/dev/null || true
