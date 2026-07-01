#!/usr/bin/env bash
# watch-telegram 단일 인스턴스 감지 — 자식 subshell(status_loop·tail) 오탐 제외
set -euo pipefail

watch_telegram_root_pids() {
  ps -ax -o pid=,ppid=,command= 2>/dev/null | awk '
    /\/watch-telegram\.sh/ && !/kill-stale/ {
      gsub(/^ +/, "")
      pid = $1
      ppid = $2
      pids[pid] = ppid
    }
    END {
      for (pid in pids) {
        if (!(pids[pid] in pids)) {
          print pid
        }
      }
    }'
}

watch_telegram_root_count() {
  local n
  n=$(watch_telegram_root_pids | wc -l | tr -d '[:space:]')
  echo "${n:-0}"
}
