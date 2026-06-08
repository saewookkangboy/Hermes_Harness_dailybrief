#!/usr/bin/env bash
# Hermes Content Studio — 서비스 시작 (Intel Mac)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WATCH_PID_FILE="/tmp/hermes-watch-telegram.pid"

echo "=== Hermes Content Studio — 서비스 시작 ==="

# 1. Ollama 확인/시작
if ! pgrep -x ollama >/dev/null 2>&1; then
  echo "[1/4] Ollama 시작..."
  open -a Ollama 2>/dev/null || ollama serve &
  sleep 3
else
  echo "[1/4] Ollama 이미 실행 중"
fi

# 2. 모델 확인
if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "[2/4] Ollama API 응답 OK"
  ollama list 2>/dev/null | head -5 || true
else
  echo "[2/4] WARNING: Ollama API 응답 없음"
fi

# 3. Hermes Gateway 확인/시작
if ! pgrep -f "hermes_cli.main gateway" >/dev/null 2>&1; then
  echo "[3/4] Hermes Gateway 시작..."
  hermes gateway run --replace &
  sleep 5
else
  echo "[3/4] Hermes Gateway 이미 실행 중 (PID: $(pgrep -f 'hermes_cli.main gateway'))"
fi

# 4. Telegram 모니터 (진행 표시 — Notion sync는 슬래시/파이프라인 담당)
if [[ "${SKIP_WATCH_TELEGRAM:-0}" != "1" ]]; then
  stale=$(ps -ax -o command= 2>/dev/null | rg -c 'watch-telegram\.sh' 2>/dev/null || echo 0)
  stale="${stale:-0}"
  if (( stale > 0 )); then
    echo "[4/4] watch-telegram 중복 ${stale}건 정리..."
    SKIP_INIT=1 "$DIR/kill-stale-watch-telegram.sh" 2>/dev/null || true
    sleep 0.5
  fi
  echo "[4/4] watch-telegram 시작 (백그라운드, 단일 인스턴스)..."
  nohup "$DIR/watch-telegram.sh" >>"$HOME/.hermes/logs/watch-telegram.log" 2>&1 &
  echo $! > "$WATCH_PID_FILE"
  echo "  PID: $(cat "$WATCH_PID_FILE") · 로그: ~/.hermes/logs/watch-telegram.log"
else
  echo "[4/4] watch-telegram 스킵 (SKIP_WATCH_TELEGRAM=1)"
fi

echo ""
echo "=== 상태 ==="
hermes cron status 2>/dev/null || echo "cron: 확인 필요"
echo "워크스페이스: ~/hermes-content-studio"
echo "디자인 시스템: ~/hermes-content-studio/Getdesign.md"
echo ""
echo "Telegram 즉시 명령 (LLM 없음): /pipeline /research /content /sync /studio"
echo ""
echo "다음 단계:"
echo "  ~/hermes-content-studio/scripts/hermes-run.sh '이번 주 리서치' --skills marketing-research"
echo "  ~/hermes-content-studio/scripts/setup-telegram-routing.sh  # 라우팅 미적용 시"
