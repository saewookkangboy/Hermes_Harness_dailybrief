#!/usr/bin/env bash
# Hermes Content Studio — Slack Bot 연결·알림·digest 스모크 테스트
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/slack_home.sh
source "$DIR/lib/slack_home.sh"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
ENV_FILE="$HOME/.hermes/.env"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
PASS=0
FAIL=0
WARN=0

pass() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
fail() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  ⚠️  $1"; WARN=$((WARN + 1)); }

run_py() {
  if [[ -x "$HERMES_PY" ]]; then "$HERMES_PY" "$@"; else python3 "$@"; fi
}

echo "=== Slack Bot 스모크 테스트 ==="
echo ""

# 1. env
echo "[1/7] 환경 변수"
if grep -q '^SLACK_BOT_TOKEN=xoxb-' "$ENV_FILE" 2>/dev/null; then
  pass "SLACK_BOT_TOKEN 설정됨 (xoxb-)"
else
  fail "SLACK_BOT_TOKEN 없음 또는 형식 오류 — setup-slack.sh 재실행"
fi
if grep -q '^SLACK_APP_TOKEN=xapp-' "$ENV_FILE" 2>/dev/null; then
  pass "SLACK_APP_TOKEN 설정됨 (xapp-)"
else
  fail "SLACK_APP_TOKEN 없음 또는 형식 오류"
fi
CH="$(studio_slack_home_channel)"
pass "SLACK_HOME_CHANNEL=${CH}"

# 2. auth.test
echo ""
echo "[2/7] Slack API auth.test"
AUTH_OUT=$(run_py - <<PY
import json, sys
sys.path.insert(0, "${WORKDIR}/scripts")
from lib.slack_notify import get_bot_token
import urllib.request
token = get_bot_token()
if not token:
    print("NO_TOKEN")
    raise SystemExit(1)
req = urllib.request.Request(
    "https://slack.com/api/auth.test",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(req, timeout=15) as r:
    d = json.loads(r.read())
if d.get("ok"):
    print(f"OK team={d.get('team')} user={d.get('user')}")
else:
    print(f"ERR {d.get('error')}")
    raise SystemExit(1)
PY
) && pass "$AUTH_OUT" || fail "auth.test 실패 — Bot Token 재발급·재설치 필요 ($AUTH_OUT)"

# 2b. scope probe (chat.postMessage + conversations.info)
echo ""
echo "[2b/7] Bot Token Scopes"
SCOPE_OUT=$("$DIR/verify-slack-scopes.sh" 2>&1) || SCOPE_RC=$?
SCOPE_RC=${SCOPE_RC:-0}
if echo "$SCOPE_OUT" | grep -q 'ALL_OK'; then
  pass "chat:write · channels:read 등 scope OK"
elif echo "$SCOPE_OUT" | grep -q 'MISSING_SCOPES'; then
  NEED=$(echo "$SCOPE_OUT" | grep '^MISSING_SCOPES:' | cut -d: -f2- | xargs)
  fail "missing_scope: ${NEED}"
  echo "       → api.slack.com → OAuth & Permissions → scope 추가 → Reinstall App"
else
  fail "scope 검증 실패"
  echo "$SCOPE_OUT" | sed 's/^/       /'
fi

# 3. channel membership
echo ""
echo "[3/7] 홈 채널 멤버십"
MEM_OUT=$(HERMES_SCRIPTS="$DIR" run_py - "$CH" <<'PY'
import json, sys, os
sys.path.insert(0, os.environ["HERMES_SCRIPTS"])
from lib.slack_notify import get_bot_token
import urllib.request
ch = sys.argv[1]
token = get_bot_token()
req = urllib.request.Request(
    f"https://slack.com/api/conversations.info?channel={ch}",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(req, timeout=15) as r:
    d = json.loads(r.read())
if not d.get("ok"):
    print(f"ERR {d.get('error')}")
    raise SystemExit(1)
c = d.get("channel", {})
name = c.get("name", "?")
member = c.get("is_member", False)
print(f"#{name} is_member={member}")
if not member:
    raise SystemExit(2)
PY
) && pass "$MEM_OUT" || {
  if [[ "$MEM_OUT" == *"is_member=False"* ]] || [[ "$MEM_OUT" == *"ERR"* ]]; then
    fail "$MEM_OUT — Slack에서 /invite @봇 실행"
  else
    fail "채널 확인 실패: $MEM_OUT"
  fi
}

# 4. ping notify
echo ""
echo "[4/7] slack-notify ping"
STAMP="$(date '+%Y-%m-%d %H:%M:%S')"
if run_py "$DIR/slack-notify.py" "$CH" "🧪 Hermes Slack 스모크 테스트 ping — ${STAMP}"; then
  pass "chat.postMessage ping 전송"
else
  fail "slack-notify 실패 (chat.postMessage)"
fi

# 5. routing config
echo ""
echo "[5/7] Hermes 라우팅"
if grep -q 'telegram-pipeline.sh qc pipeline' "$HOME/.hermes/config.yaml" 2>/dev/null; then
  pass "quick_commands /pipeline"
else
  fail "quick_commands 미설정 — setup-slack-routing.sh"
fi
if grep -q 'C0B8CN2EA05' "$HOME/.hermes/config.yaml" 2>/dev/null; then
  pass "free_response_channels #일반데이터"
else
  warn "free_response_channels 확인 필요"
fi

# 6. gateway
echo ""
echo "[6/7] Gateway"
if pgrep -f "hermes_cli.main gateway" >/dev/null 2>&1; then
  pass "Gateway 실행 중 (PID $(pgrep -f 'hermes_cli.main gateway' | head -1))"
else
  fail "Gateway 미실행 — hermes gateway restart"
fi

# 7. daily log (compact)
echo ""
echo "[7/7] slack-daily-log (2026-06-06)"
if run_py "$DIR/slack-daily-log.py" 2026-06-06 --send 2>&1 | tee /tmp/slack-daily-log-test.log | grep -q 'Slack 전송 완료'; then
  pass "Daily digest Slack 전송"
elif grep -q 'digest' /tmp/slack-daily-log-test.log 2>/dev/null; then
  warn "digest 빌드됨 — 전송 일부 실패 가능 (로그 확인)"
else
  fail "slack-daily-log 실패"
fi

# optional qc studio (non-fatal)
echo ""
echo "[bonus] telegram-pipeline qc studio"
"$DIR/telegram-pipeline.sh" qc studio 2>&1 | tail -5 || true

echo ""
echo "=== 결과: PASS=${PASS} FAIL=${FAIL} WARN=${WARN} ==="
[[ "$FAIL" -eq 0 ]]
