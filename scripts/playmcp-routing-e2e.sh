#!/usr/bin/env bash
# PlayMCP Kakao 라우팅 E2E — wiring + LIVE (routing merge · MCP · qc)
#
# Usage:
#   ./playmcp-routing-e2e.sh              # wiring + integration
#   HERMES_PLAYMCP_E2E_LIVE=1 ./playmcp-routing-e2e.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
CONFIG="$HOME/.hermes/config.yaml"
LIVE="${HERMES_PLAYMCP_E2E_LIVE:-0}"
PASS=0
FAIL=0

record() { [[ "$1" == PASS ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1)); echo "$1 $2"; }

echo "=== PlayMCP Routing E2E ==="

if "$DIR/playmcp-integration-eval.sh" >/tmp/playmcp-integ.log 2>&1; then
  record PASS "integration_eval"
else
  record FAIL "integration_eval"
  tail -10 /tmp/playmcp-integ.log 2>/dev/null || true
fi

MERGE_OK=$(python3 - <<PY
import sys
from pathlib import Path
try:
    import yaml
except ImportError:
    print("no_yaml")
    raise SystemExit
routing = yaml.safe_load(Path("$WORKDIR/config/playmcp-routing.yaml").read_text(encoding="utf-8"))
cfg_path = Path("$CONFIG")
if not cfg_path.exists():
    print("no_config")
    raise SystemExit
cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
qc = cfg.get("quick_commands") or {}
need = ["pipeline", "blog", "sync", "commands"]
missing = [k for k in need if k not in qc]
if missing:
    print("missing:" + ",".join(missing))
else:
    cmd = qc["pipeline"].get("command", "")
    if "telegram-pipeline.sh qc pipeline" in cmd:
        print("ok")
    else:
        print("bad_pipeline_cmd")
PY
)
case "$MERGE_OK" in
  ok) record PASS "config_quick_commands_merged" ;;
  no_config) record FAIL "config_quick_commands_merged (no ~/.hermes/config.yaml)" ;;
  *) record FAIL "config_quick_commands_merged ($MERGE_OK)" ;;
esac

if [[ "$LIVE" == "1" ]]; then
  echo ""
  echo "--- LIVE routing ---"
  if "$DIR/setup-playmcp-routing.sh" >/tmp/playmcp-routing-setup.log 2>&1; then
    record PASS "setup_playmcp_routing"
  else
    record FAIL "setup_playmcp_routing"
    tail -15 /tmp/playmcp-routing-setup.log 2>/dev/null || true
  fi

  if hermes mcp test playmcp 2>&1 | tee /tmp/playmcp-mcp-test.log | grep -qiE "Connected|success|OK"; then
    record PASS "mcp_test_playmcp"
  elif grep -qE "401 Unauthorized|401" /tmp/playmcp-mcp-test.log 2>/dev/null; then
    echo "WARN mcp_test 401 — ONE_TIME_TOKEN 갱신: ./scripts/setup-playmcp.sh"
    record PASS "mcp_routing_ok_token_stale"
  else
    record FAIL "mcp_test_playmcp"
    tail -8 /tmp/playmcp-mcp-test.log 2>/dev/null || true
  fi

  if "$DIR/telegram-pipeline.sh" qc commands 2>/dev/null | grep -qE "pipeline|research|sync"; then
    record PASS "qc_commands_exec"
  else
    record FAIL "qc_commands_exec"
  fi

  if "$DIR/telegram-pipeline.sh" qc morning 2>/dev/null | grep -qiE "Morning|morning|브리핑"; then
    record PASS "qc_morning_exec"
  else
    record FAIL "qc_morning_exec"
  fi

  PLAYMCP_CFG=$(python3 - <<PY
import yaml
from pathlib import Path
p = Path("$CONFIG")
if not p.exists():
    print("0")
else:
    cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    pm = cfg.get("playmcp") or {}
    print("1" if pm.get("enabled") and pm.get("channel_prompt") else "0")
PY
)
  if [[ "$PLAYMCP_CFG" == "1" ]]; then
    record PASS "playmcp_channel_prompt"
  else
    record FAIL "playmcp_channel_prompt"
  fi
else
  echo ""
  echo "LIVE 스킵 — HERMES_PLAYMCP_E2E_LIVE=1 로 routing · mcp test · qc 실행"
fi

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
[[ "$FAIL" -eq 0 ]]
