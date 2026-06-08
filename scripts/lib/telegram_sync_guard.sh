#!/usr/bin/env bash
# Telegram Notion sync 중복 방지 — 파이프라인·watch-telegram 공용
# shellcheck shell=bash

_tsg_workdir() {
  echo "${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
}

_tsg_lock_path() {
  echo "$(_tsg_workdir)/.harness/telegram-sync.lock"
}

# 파이프라인/슬래시 sync 시작 시 호출 (watch 로그 파싱 금지 — 오래된 stamp로 lock 덮어쓰기 방지)
telegram_sync_begin() {
  local stamp="${1:-}"
  [[ -n "$stamp" ]] || return 0
  mkdir -p "$(_tsg_workdir)/.harness"
  local lock="$(_tsg_lock_path)"
  if [[ -f "$lock" ]]; then
    local old_stamp ts pid
    IFS=: read -r old_stamp ts pid < "$lock" || true
    # ISO 날짜 문자열 비교 — 더 오래된 stamp로 lock 갱신 금지
    if [[ -n "$old_stamp" && "$stamp" < "$old_stamp" ]]; then
      echo "ℹ️  sync lock 유지 (${old_stamp}) — ${stamp} 무시" >&2
      return 0
    fi
  fi
  printf '%s:%s:%s\n' "$stamp" "$(date +%s)" "$$" > "$lock"
}

# archive 완료 후 호출 (선택)
telegram_sync_end() {
  rm -f "$(_tsg_lock_path)"
}

# watch-telegram post-sync 스킵 여부 (0=스킵, 1=실행 가능)
telegram_sync_should_skip_watch() {
  local lock max_age="${TELEGRAM_SYNC_GUARD_SEC:-300}"
  lock="$(_tsg_lock_path)"
  [[ -f "$lock" ]] || return 1
  local stamp ts pid now
  IFS=: read -r stamp ts pid < "$lock" || return 1
  now=$(date +%s)
  if [[ -n "$ts" ]] && (( now - ts < max_age )); then
    echo "ℹ️  파이프라인 Notion sync 진행/완료 (${stamp}) — watch post-sync skip" >&2
    return 0
  fi
  return 1
}
