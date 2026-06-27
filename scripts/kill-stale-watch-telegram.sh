#!/usr/bin/env bash
# 중복 watch-telegram 프로세스 정리 (Notion sync 2중 실행 방지)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
LOCK="$WORKDIR/.harness/watch-telegram.lock"
PID_FILE="/tmp/hermes-watch-telegram.pid"

if [[ "${1:-}" == "--check" ]]; then
  n=$(ps -ax -o pid=,command= 2>/dev/null | rg -c 'watch-telegram\.sh' || echo 0)
  if [[ "$n" -gt 1 ]]; then
    echo "DUPLICATE watch-telegram count=$n"
    exit 0
  fi
  echo "OK watch-telegram count=$n"
  exit 0
fi

count=0
while read -r pid; do
  [[ -z "$pid" ]] && continue
  kill "$pid" 2>/dev/null && count=$((count + 1)) || true
done < <(ps -ax -o pid=,command= 2>/dev/null | rg 'watch-telegram\.sh' | awk '{print $1}' || true)

rm -f "$LOCK" "$PID_FILE" 2>/dev/null || true
echo "watch-telegram 정리 완료 — 종료 ${count}건"
echo "재시작: ~/hermes-content-studio/scripts/start-services.sh"
