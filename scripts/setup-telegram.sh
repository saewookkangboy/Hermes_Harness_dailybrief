#!/usr/bin/env bash
# Hermes Content Studio — Telegram Bot 연결 (Discord 대체, 가장 간편)
#
# WhatsApp 대비 선택 이유:
#   - BotFather 토큰만으로 5분 내 연결 (QR/Node 브릿지 불필요)
#   - Long polling 기본 — 공개 URL 불필요
#   - cron deliver: telegram 또는 telegram:CHAT_ID
#
# Usage:
#   TELEGRAM_BOT_TOKEN=123456:ABC... TELEGRAM_ALLOWED_USERS=123456789 ./setup-telegram.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HOME/.hermes/.env"

echo "=== Hermes Telegram Bot 설정 ==="
echo ""
echo "사전 준비 (2분):"
echo "  1. Telegram에서 @BotFather → /newbot"
echo "  2. 봇 이름·username 설정 → API 토큰 복사"
echo "  3. @userinfobot 에게 /start → 본인 User ID 확인"
echo ""

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  read -rp "TELEGRAM_BOT_TOKEN: " TELEGRAM_BOT_TOKEN
fi
if [[ -z "${TELEGRAM_ALLOWED_USERS:-}" ]]; then
  read -rp "TELEGRAM_ALLOWED_USERS (숫자 ID): " TELEGRAM_ALLOWED_USERS
fi

if [[ ! "$TELEGRAM_BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
  echo "오류: TELEGRAM_BOT_TOKEN 형식이 올바르지 않습니다 (예: 123456789:ABCdef...)"
  exit 1
fi

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

# Discord 비활성화
comment_env() {
  local key="$1"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^${key}=|# ${key}=|" "$ENV_FILE"
  fi
}

touch "$ENV_FILE"
echo "[1/4] Discord 토큰 비활성화..."
comment_env "DISCORD_BOT_TOKEN"
comment_env "DISCORD_ALLOWED_USERS"
comment_env "DISCORD_HOME_CHANNEL"

echo "[2/4] Telegram 토큰 설정..."
update_env "TELEGRAM_BOT_TOKEN" "$TELEGRAM_BOT_TOKEN"
update_env "TELEGRAM_ALLOWED_USERS" "$TELEGRAM_ALLOWED_USERS"
# DM chat id = allowed user id (Permalink·post-sync용)
update_env "TELEGRAM_CHAT_ID" "$TELEGRAM_ALLOWED_USERS"
rm -f "${ENV_FILE}.bak"

echo "[3/4] Gateway 재시작..."
hermes gateway restart
sleep 3

echo "[4/4] 연결 확인..."
if pgrep -f "hermes_cli.main gateway" >/dev/null 2>&1; then
  echo "  ✓ Gateway 실행 중"
else
  echo "  ⚠️  Gateway 확인 필요: hermes gateway status"
fi

echo "[5/5] 결정적 라우팅 (quick_commands + channel_prompts)..."
TELEGRAM_ALLOWED_USERS="${TELEGRAM_ALLOWED_USERS:-}" "$DIR/setup-telegram-routing.sh" || \
  echo "  ⚠️  setup-telegram-routing.sh 수동 실행 필요"

echo ""
echo "=== 완료 ==="
echo "Telegram에서 봇에게 /start 를 보내 테스트하세요."
echo "즉시 실행 (LLM 없음): /pipeline /research /content /sync /studio"
echo "홈 채널 설정: 봇 DM에서 /sethome"
echo "cron deliver: hermes cron edit <id> --deliver telegram"
