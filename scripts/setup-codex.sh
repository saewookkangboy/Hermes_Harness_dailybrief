#!/usr/bin/env bash
# Hermes Content Studio — OpenAI Codex (ChatGPT 구독) 연동
#
# Usage:
#   ./setup-codex.sh              # Codex CLI 설치 + Hermes OAuth 연동
#   ./setup-codex.sh --import     # ~/.codex/auth.json → Hermes 가져오기
#   ./setup-codex.sh --login      # 새 device-code 로그인
#
set -euo pipefail

HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
CODEX_BIN="$HOME/.hermes/node/bin/codex"
MODE="${1:-setup}"

echo "=== Hermes Content Studio — Codex 연동 ==="
echo ""

ensure_codex_cli() {
  if [[ -x "$CODEX_BIN" ]]; then
    echo "[1/4] Codex CLI: $($CODEX_BIN --version)"
    return
  fi
  echo "[1/4] Codex CLI 설치 중..."
  npm install -g @openai/codex --prefix "$HOME/.hermes/node"
  echo "  → $CODEX_BIN"
}

import_codex_tokens() {
  echo "[2/4] Codex CLI 토큰 → Hermes 가져오기..."
  if [[ ! -x "$HERMES_PY" ]]; then
    echo "오류: Hermes venv 없음 ($HERMES_PY)" >&2
    exit 1
  fi
  "$HERMES_PY" - <<'PY'
from hermes_cli.auth import _import_codex_cli_tokens, _save_codex_tokens, get_codex_auth_status

tokens = _import_codex_cli_tokens()
if not tokens:
    raise SystemExit("❌ ~/.codex/auth.json 에 유효한 토큰이 없습니다. 'codex login' 실행 후 재시도.")
_save_codex_tokens(tokens)
status = get_codex_auth_status()
if not status.get("logged_in"):
    raise SystemExit("❌ Hermes Codex 인증 저장 실패")
print(f"✅ Hermes Codex 인증 완료 ({status.get('source', 'imported')})")
PY
}

login_codex() {
  echo "[2/4] Hermes Codex device-code 로그인..."
  hermes auth add openai-codex
}

verify_auth() {
  echo "[3/4] 인증 확인..."
  if hermes auth status openai-codex 2>&1 | grep -q "logged in"; then
    echo "✅ openai-codex: logged in"
  else
    echo "❌ openai-codex 인증 실패" >&2
    exit 1
  fi
}

show_config() {
  echo "[4/4] 설정 요약"
  echo ""
  echo "  Primary (cron/기본):  Ollama gemma4"
  echo "  Fallback:             openai-codex / gpt-5.3-codex"
  echo "  품질 경로 (자동 Codex):"
  echo "    - claude-design HTML 덱"
  echo "    - HERMES_ENHANCE=1 polish"
  echo ""
  echo "  Gateway 재시작 (Telegram 반영):"
  echo "    launchctl kickstart -k gui/\$(id -u)/com.hermes.gateway 2>/dev/null || true"
  echo ""
  echo "  Codex app-server (선택, Hermes 세션에서):"
  echo "    /codex-runtime codex_app_server"
}

case "$MODE" in
  --import)
    ensure_codex_cli
    import_codex_tokens
    verify_auth
    show_config
    ;;
  --login)
    ensure_codex_cli
    login_codex
    verify_auth
    show_config
    ;;
  setup|*)
    ensure_codex_cli
    if hermes auth status openai-codex 2>&1 | grep -q "logged in"; then
      echo "[2/4] 기존 Hermes Codex 인증 유지"
    elif [[ -f "$HOME/.codex/auth.json" ]]; then
      import_codex_tokens
    else
      echo "  ~/.codex/auth.json 없음 — device-code 로그인 필요"
      login_codex
    fi
    verify_auth
    show_config
    ;;
esac

echo ""
echo "=== Codex 연동 완료 ==="
