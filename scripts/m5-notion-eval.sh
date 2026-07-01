#!/usr/bin/env bash
# M5 Notion archive E2E — setup_mcp 노이즈 + archive 배선
#
# Usage:
#   ./m5-notion-eval.sh [YYYY-MM-DD]              # wiring only
#   HERMES_M5_E2E_LIVE=1 ./m5-notion-eval.sh DATE # archive-to-notion --force
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="${HERMES_PY:-$HOME/.hermes/hermes-agent/venv/bin/python}"
STAMP="${1:-$(date +%Y-%m-%d)}"
LIVE="${HERMES_M5_E2E_LIVE:-0}"
PASS=0
FAIL=0

record() { [[ "$1" == PASS ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1)); echo "$1 $2"; }

RUN_PY() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

echo "=== M5 Notion Eval — $STAMP ==="

if [[ -x "$DIR/archive-to-notion.sh" ]]; then
  record PASS "archive-to-notion.sh"
else
  record FAIL "archive-to-notion.sh missing"
fi

MCP_NOISE=$(RUN_PY - <<PY 2>&1
import sys
sys.path.insert(0, "$DIR")
from lib.notion_client import setup_mcp
setup_mcp()
PY
)
if echo "$MCP_NOISE" | grep -qiE "MCP server 'playmcp'|playmcp.*failed|unhandled errors"; then
  record FAIL "m5_mcp_playmcp_noise"
else
  record PASS "m5_mcp_playmcp_suppressed"
fi

BRIEF="$WORKDIR/content/research/${STAMP}_brief.md"
if [[ -f "$BRIEF" ]]; then
  record PASS "brief_artifact"
else
  record FAIL "brief_artifact missing"
fi

if [[ "$LIVE" == "1" ]]; then
  echo ""
  echo "--- Live M5 archive (--force) ---"
  if "$DIR/archive-to-notion.sh" "$STAMP" --force >/tmp/m5-notion-live.log 2>&1; then
    record PASS "archive_force_ok"
    if grep -qiE "playmcp.*failed|MCP server 'playmcp'" /tmp/m5-notion-live.log; then
      record FAIL "archive_log_playmcp_noise"
    else
      record PASS "archive_log_clean"
    fi
    COUNT=$(grep -oE '"count":\s*[0-9]+' /tmp/m5-notion-live.log | tail -1 | grep -oE '[0-9]+' || true)
    if [[ -n "${COUNT:-}" ]] && (( COUNT >= 8 )); then
      record PASS "archive_count_ge_8"
    else
      record FAIL "archive_count_lt_8 (${COUNT:-?})"
    fi
  else
    record FAIL "archive_force_failed"
    tail -20 /tmp/m5-notion-live.log 2>/dev/null || true
  fi
else
  echo ""
  echo "Live M5 스킵 — HERMES_M5_E2E_LIVE=1 로 archive --force 실운영"
fi

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
[[ "$FAIL" -eq 0 ]]
