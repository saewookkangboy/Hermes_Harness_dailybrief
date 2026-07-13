#!/usr/bin/env bash
# Notion MCP OAuth 재인증 — 대화형 TTY 전용
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_PY="${HERMES_PY:-$HOME/.hermes/hermes-agent/venv/bin/python}"

if [[ ! -t 0 || ! -t 1 ]]; then
  echo "❌ 대화형 터미널이 필요합니다."
  echo "   로컬 Terminal/iTerm에서 실행: $DIR/reauth-notion-mcp.sh"
  exit 1
fi

echo "=== Notion MCP OAuth 재인증 ==="
echo ""
echo "1) 브라우저에서 Notion 승인"
echo "2) hermes mcp test notion 으로 연결 확인"
echo ""

hermes mcp login notion
hermes mcp test notion

echo ""
echo "--- OAuth 상태 ---"
"$HERMES_PY" - <<'PY'
import sys
sys.path.insert(0, "/Users/chunghyo/hermes-content-studio/scripts")
from lib.notion_client import load_config, setup_mcp_verified
from lib.notion_oauth import check_notion_oauth_status, required_notion_tools

cfg = load_config()
registry = setup_mcp_verified(cfg=cfg)
status = check_notion_oauth_status(required_tools=required_notion_tools(cfg), registry=registry)
print(status.detail)
if status.missing_tools:
    print("missing:", ", ".join(status.missing_tools))
raise SystemExit(0 if status.ok else 1)
PY

echo ""
echo "✅ Notion OAuth 준비 완료"
echo "백필: $DIR/backfill-notion-archive.sh 2026-07-06 2026-07-09"
