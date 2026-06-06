#!/usr/bin/env bash
# Hermes Content Studio — Slack Bot Token 설정
# Usage:
#   SLACK_BOT_TOKEN=xoxb-... SLACK_APP_TOKEN=xapp-... ./setup-slack.sh
#   SLACK_HOME_CHANNEL=C0B8CN2EA05 SLACK_HOME_CHANNEL_NAME=일반데이터 (optional)
set -euo pipefail

ENV_FILE="$HOME/.hermes/.env"
MANIFEST="$HOME/.hermes/slack-manifest.json"
WORKDIR="$HOME/hermes-content-studio"

echo "=== Hermes Slack Bot 설정 ==="

# 1. 매니페스트 생성
if [ ! -f "$MANIFEST" ]; then
  echo "[1/5] Slack 앱 매니페스트 생성..."
  hermes slack manifest --write
else
  echo "[1/5] 매니페스트 존재: $MANIFEST"
fi

# 2. 토큰 입력
if [ -z "${SLACK_BOT_TOKEN:-}" ]; then
  read -rp "SLACK_BOT_TOKEN (xoxb-...): " SLACK_BOT_TOKEN
fi
if [ -z "${SLACK_APP_TOKEN:-}" ]; then
  read -rp "SLACK_APP_TOKEN (xapp-...): " SLACK_APP_TOKEN
fi

if [[ ! "$SLACK_BOT_TOKEN" =~ ^xoxb- ]] || [[ ! "$SLACK_APP_TOKEN" =~ ^xapp- ]]; then
  echo "오류: 토큰 형식이 올바르지 않습니다."
  echo "  SLACK_BOT_TOKEN → xoxb- 로 시작"
  echo "  SLACK_APP_TOKEN → xapp- 로 시작"
  echo ""
  echo "토큰 발급:"
  echo "  1. https://api.slack.com/apps → Create New App → From manifest"
  echo "  2. $MANIFEST 내용 붙여넣기"
  echo "  3. Socket Mode 활성화 → App Token (connections:write) 생성"
  echo "  4. Install App → Bot User OAuth Token (xoxb-) 복사 — App Token(xapp-)과 다름!"
  exit 1
fi

if [[ ${#SLACK_BOT_TOKEN} -lt 50 ]]; then
  echo "오류: SLACK_BOT_TOKEN이 너무 짧습니다 (${#SLACK_BOT_TOKEN}자)."
  echo "  api.slack.com → Your App → OAuth & Permissions → Bot User OAuth Token 전체 복사"
  exit 1
fi

echo "[2/6] Slack API auth.test 검증..."
DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
run_py() { if [[ -x "$HERMES_PY" ]]; then "$HERMES_PY" "$@"; else python3 "$@"; fi; }

AUTH_ERR=$(SLACK_BOT_TOKEN="$SLACK_BOT_TOKEN" run_py - <<'PY'
import json, os, sys, urllib.request
token = os.environ["SLACK_BOT_TOKEN"].strip()
req = urllib.request.Request(
    "https://slack.com/api/auth.test",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(req, timeout=15) as r:
    d = json.loads(r.read())
if d.get("ok"):
    print(f"OK:{d.get('team')}:{d.get('user')}")
else:
    print(d.get("error", "unknown"))
    sys.exit(1)
PY
) || {
  echo "❌ auth.test 실패: ${AUTH_ERR:-invalid_auth}"
  echo ""
  echo "확인:"
  echo "  • Bot User OAuth Token (xoxb-) — App-Level Token(xapp-) 아님"
  echo "  • Install App to Workspace 후 토큰 재복사"
  echo "  • 토큰 앞뒤 공백·줄바꿈 없이 전체 붙여넣기"
  exit 1
}
echo "  ✓ auth.test ${AUTH_ERR#OK:}"

# 허용 사용자 (기본: 박충효 U05E547KR0D)
SLACK_ALLOWED_USERS="${SLACK_ALLOWED_USERS:-U05E547KR0D}"
# 홈 채널 (기본: #일반데이터)
SLACK_HOME_CHANNEL="${SLACK_HOME_CHANNEL:-C0B8CN2EA05}"
SLACK_HOME_CHANNEL_NAME="${SLACK_HOME_CHANNEL_NAME:-일반데이터}"

# 3. .env 업데이트
echo "[3/6] ~/.hermes/.env 업데이트..."
touch "$ENV_FILE"

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

update_env "SLACK_BOT_TOKEN" "$SLACK_BOT_TOKEN"
update_env "SLACK_APP_TOKEN" "$SLACK_APP_TOKEN"
update_env "SLACK_ALLOWED_USERS" "$SLACK_ALLOWED_USERS"

if [ -n "${SLACK_HOME_CHANNEL:-}" ]; then
  update_env "SLACK_HOME_CHANNEL" "$SLACK_HOME_CHANNEL"
fi
if [ -n "${SLACK_HOME_CHANNEL_NAME:-}" ]; then
  update_env "SLACK_HOME_CHANNEL_NAME" "$SLACK_HOME_CHANNEL_NAME"
fi

rm -f "${ENV_FILE}.bak"

# 4. Gateway 재시작
echo "[4/6] Gateway 재시작..."
hermes gateway restart

# 5. 연결 확인
echo "[5/6] Gateway 상태 확인..."
sleep 3
if pgrep -f "hermes_cli.main gateway" >/dev/null 2>&1; then
  echo "  ✓ Gateway 실행 중 (PID: $(pgrep -f 'hermes_cli.main gateway'))"
else
  echo "  ⚠️  Gateway 미실행 — hermes gateway status 확인"
fi

# 6. cron deliver 업데이트 (SLACK_HOME_CHANNEL 설정 시)
if [ -n "${SLACK_HOME_CHANNEL_NAME:-}" ]; then
  DELIVER_TARGET="slack:#${SLACK_HOME_CHANNEL_NAME}"
  echo "[6/6] cron deliver → $DELIVER_TARGET (수동 확인 권장)"
  echo "  hermes cron list 로 작업 ID 확인 후:"
  echo "  hermes cron edit <id> --deliver $DELIVER_TARGET"
else
  echo "[6/6] SLACK_HOME_CHANNEL_NAME 미설정 — cron deliver는 local 유지"
  echo "  채널 설정 후: SLACK_HOME_CHANNEL_NAME=채널명 ./setup-slack.sh"
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[7/7] 결정적 라우팅 + 스모크 테스트..."
SLACK_HOME_CHANNEL="${SLACK_HOME_CHANNEL:-}" "$DIR/setup-slack-routing.sh" || \
  echo "  ⚠️  setup-slack-routing.sh 수동 실행 필요"

if "$DIR/slack-smoke-test.sh"; then
  echo "  ✓ slack-smoke-test PASS"
else
  echo "  ⚠️  slack-smoke-test 일부 실패 — #일반데이터에 /invite @봇 확인"
fi

echo ""
echo "=== 완료 ==="
echo "Slack #${SLACK_HOME_CHANNEL_NAME}에서 /pipeline /research /content /sync /studio (LLM 없음)"
echo "사전: @Hermes 봇을 #${SLACK_HOME_CHANNEL_NAME}에 /invite"
