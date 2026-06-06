#!/usr/bin/env bash
# Hermes Content Studio — PlayMCP (Kakao) MCP-Gateway 연결
# Slack Bot과 동일한 커맨더(명령) 채널 역할 부여
#
# Usage:
#   ONE_TIME_TOKEN=ott_... ./setup-playmcp.sh
#   또는 인터랙티브로 OTT 입력
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/hermes-node-path.sh
source "${SCRIPT_DIR}/lib/hermes-node-path.sh"

ENV_FILE="$HOME/.hermes/.env"
CONFIG_FILE="$HOME/.hermes/config.yaml"
MCPORTER_DIR="$HOME/.mcporter"
MCPORTER_CREDS="$MCPORTER_DIR/credentials.json"
PLAYMCP_URL="https://playmcp.kakao.com/mcp"
PLAYMCP_CLIENT_ID="HElMUWdVoroTsrXxezeTSemg8gXzzCKWARb5MJux8gY"
VAULT_HASH="92ef5a9fd655a681"
VAULT_KEY="mcp-gateway|${VAULT_HASH}"

echo "=== PlayMCP MCP-Gateway 연결 (Hermes Commander) ==="

# 0. OTT 확인
if [ -z "${ONE_TIME_TOKEN:-}" ]; then
  echo ""
  echo "PlayMCP OTT가 필요합니다:"
  echo "  1. https://playmcp.kakao.com 로그인"
  echo "  2. https://playmcp.kakao.com/toolbox → 'OpenClaw와 연결'"
  echo "  3. 생성된 프롬프트에서 oneTimeToken 복사"
  echo ""
  read -rp "ONE_TIME_TOKEN: " ONE_TIME_TOKEN
fi

if [ -z "$ONE_TIME_TOKEN" ]; then
  echo "오류: ONE_TIME_TOKEN이 비어 있습니다."
  exit 1
fi

# 1. mcporter 설치 + 셸 PATH (검증용)
MCPORTER_BIN="${HERMES_NODE_BIN}/mcporter"
if [[ -x "$MCPORTER_BIN" ]]; then
  echo "[1/7] mcporter 이미 설치됨 ($MCPORTER_BIN)"
else
  echo "[1/7] mcporter 설치..."
  mkdir -p "$HERMES_NODE_PREFIX"
  npm install -g mcporter --prefix "$HERMES_NODE_PREFIX"
fi
hermes_ensure_node_path_in_shell

# 2. OTT → 액세스 토큰 교환
echo "[2/7] OTT 교환 중..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  'https://playmcp.kakao.com/api/v1/auths/otts:exchange' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d "{\"tokenValue\":\"${ONE_TIME_TOKEN}\"}")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  echo "오류: OTT 교환 실패 (HTTP $HTTP_CODE)"
  echo "$BODY"
  echo ""
  echo "OTT가 만료되었을 수 있습니다. PlayMCP 도구함에서 새 연결 프롬프트를 생성하세요."
  exit 1
fi

ACCESS_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['accessToken']['tokenValue'])" 2>/dev/null)
REFRESH_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['refreshToken']['tokenValue'])" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ] || [ -z "$REFRESH_TOKEN" ]; then
  echo "오류: 토큰 파싱 실패"
  echo "$BODY"
  exit 1
fi

echo "  ✓ 액세스 토큰 발급 완료"

# 3. ~/.hermes/.env 업데이트
echo "[3/7] ~/.hermes/.env 업데이트..."
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

update_env "MCP_PLAYMCP_API_KEY" "$ACCESS_TOKEN"
update_env "MCP_PLAYMCP_REFRESH_TOKEN" "$REFRESH_TOKEN"
rm -f "${ENV_FILE}.bak"

# 4. mcporter credentials.json
echo "[4/7] mcporter credentials 설정..."
mkdir -p "$MCPORTER_DIR"
NOW_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

python3 << PYEOF
import json, os
path = os.path.expanduser("$MCPORTER_CREDS")
data = {"version": 1, "entries": {}}
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)
data.setdefault("entries", {})["$VAULT_KEY"] = {
    "serverName": "mcp-gateway",
    "serverUrl": "$PLAYMCP_URL",
    "tokens": {
        "access_token": "$ACCESS_TOKEN",
        "token_type": "Bearer",
        "refresh_token": "$REFRESH_TOKEN"
    },
    "clientInfo": {"client_id": "$PLAYMCP_CLIENT_ID"},
    "updatedAt": "$NOW_ISO"
}
with open(path, "w") as f:
    json.dump(data, f, indent=2)
print("  ✓", path)
PYEOF

# 5. mcporter 서버 정의 (~/.mcporter/mcporter.json)
echo "[5/7] mcporter mcp-gateway 서버 등록..."
MCPORTER_CONFIG="${MCPORTER_DIR}/mcporter.json"
if [[ -f "$MCPORTER_CONFIG" ]] && grep -q '"mcp-gateway"' "$MCPORTER_CONFIG" 2>/dev/null; then
  echo "  ✓ mcporter mcp-gateway 이미 등록됨"
else
  "$MCPORTER_BIN" config add mcp-gateway "$PLAYMCP_URL" --auth oauth --scope home
  echo "  ✓ mcporter mcp-gateway 등록됨"
fi

# 6. Hermes config.yaml — playmcp enabled
echo "[6/7] Hermes MCP 활성화..."
if grep -A6 "playmcp:" "$CONFIG_FILE" | grep -q "enabled: false"; then
  sed -i.bak '/^  playmcp:/,/^  [a-z]/ s/enabled: false/enabled: true/' "$CONFIG_FILE"
  rm -f "${CONFIG_FILE}.bak"
  echo "  ✓ playmcp enabled: true"
else
  echo "  ✓ playmcp config 확인됨"
fi

# 7. 연결 검증 + Gateway 재시작
echo "[7/7] 연결 검증 및 Gateway 재시작..."
if hermes mcp test playmcp 2>&1 | grep -q "Connected"; then
  echo "  ✓ hermes mcp test playmcp 성공"
else
  echo "  ⚠️  hermes mcp test playmcp — 수동 확인: hermes mcp test playmcp"
fi
if "$MCPORTER_BIN" list mcp-gateway 2>&1 | grep -q "mcp-gateway"; then
  echo "  ✓ mcporter list mcp-gateway 성공"
else
  echo "  ⚠️  mcporter list mcp-gateway — 수동 확인: mcporter list mcp-gateway"
fi

hermes gateway restart
sleep 3

echo ""
echo "=== PlayMCP Commander 연결 완료 ==="
echo ""
echo "Slack과 동일한 커맨더 역할:"
echo "  hermes chat -s playmcp-commander,content-pipeline"
echo "  hermes -z \"이번 주 리서치 브리프 작성\" --skills playmcp-commander,marketing-research"
echo ""
echo "도구함에 담긴 MCP 서버 도구가 Hermes에서 사용 가능합니다."
echo "검증: hermes mcp list && mcporter list mcp-gateway"
