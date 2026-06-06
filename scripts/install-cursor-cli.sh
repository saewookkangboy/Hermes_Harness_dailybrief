#!/usr/bin/env bash
# Hermes Content Studio — Cursor CLI + cursor-agent 설치
#
# Usage:
#   ./install-cursor-cli.sh              # cursor-agent 설치 + IDE symlink
#   ./install-cursor-cli.sh --check      # 설치 상태만 확인
#   ./install-cursor-cli.sh --symlink    # IDE symlink만 (agent 이미 있을 때)
#
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/cursor-cli.sh
source "$DIR/lib/cursor-cli.sh"

MODE="${1:-setup}"

check_status() {
  echo "=== Cursor CLI 상태 ==="
  echo ""
  local agent ide
  agent=$(cursor_cli_resolve_agent 2>/dev/null || echo "(없음)")
  ide=$(cursor_cli_resolve_ide 2>/dev/null || echo "(없음)")
  echo "  cursor-agent: $agent"
  if [[ -x "$agent" ]]; then
    echo "    version: $(cursor_cli_version)"
  fi
  echo "  cursor (IDE): $ide"
  if [[ -x "$ide" ]]; then
    echo "    version: $($ide --version 2>/dev/null || echo '?')"
  fi
  echo ""
  if cursor_cli_agent_ready; then
    echo "✅ CLI 자동화 준비 완료"
    if cursor_cli_auth_ready; then
      echo "✅ cursor-agent 인증: OK"
    else
      echo "⚠️  cursor-agent 인증 필요: cursor-agent login (또는 CURSOR_API_KEY)"
    fi
    echo ""
    echo "  핸드오프 실행:"
    echo "    ~/hermes-content-studio/scripts/run-cursor-handoff.sh --latest"
    echo ""
    echo "  Telegram /automate 후 자동 실행:"
    echo "    HERMES_CURSOR_AUTO=1 (기본값)"
    exit 0
  fi
  echo "❌ cursor-agent 미설치"
  echo "  ./install-cursor-cli.sh 실행 또는:"
  echo "  curl -fsSL https://cursor.com/install | bash"
  exit 1
}

install_agent() {
  if cursor_cli_agent_ready; then
    echo "[1/2] cursor-agent: $(cursor_cli_resolve_agent) ($(cursor_cli_version))"
    return 0
  fi
  echo "[1/2] cursor-agent 설치 중 (cursor.com/install)..."
  curl -fsSL https://cursor.com/install | bash
}

install_symlinks() {
  echo "[2/2] IDE symlink..."
  cursor_cli_ensure_symlinks
  if [[ -L "$CURSOR_IDE_BIN" || -x "$CURSOR_IDE_BIN" ]]; then
    echo "  → $CURSOR_IDE_BIN"
  elif [[ ! -x "$CURSOR_APP_BIN" ]]; then
    echo "  ⚠️  Cursor.app 없음 — IDE symlink 생략 (agent만 사용 가능)"
  fi
}

case "$MODE" in
  --check)
    check_status
    ;;
  --symlink)
    install_symlinks
    check_status
    ;;
  setup|*)
    echo "=== Hermes Content Studio — Cursor CLI 설치 ==="
    echo ""
    install_agent
    install_symlinks
    echo ""
    check_status
    ;;
esac
