#!/usr/bin/env bash
# Keyword research / staging smoke (no live web required for core checks)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Research Keyword / Staging Eval ==="

grep -q research-pending "$WORKDIR/config/slack-routing.yaml" && record PASS "slack_routing" || record FAIL "slack_routing"
grep -q research-approve "$WORKDIR/config/telegram-routing.yaml" && record PASS "telegram_routing" || record FAIL "telegram_routing"
grep -q research-pending "$WORKDIR/config/playmcp-routing.yaml" && record PASS "playmcp_routing" || record FAIL "playmcp_routing"
grep -q '리서치 승인' "$WORKDIR/config/agent-commands.yaml" && record PASS "agent_commands" || record FAIL "agent_commands"
grep -q 'bare 승인' "$WORKDIR/config/slack-routing.yaml" && record PASS "nl_collision_docs" || record FAIL "nl_collision_docs"

"$DIR/telegram-pipeline.sh" qc research-pending 2>/dev/null | grep -q "research staging" && record PASS "qc_research_pending" || record FAIL "qc_research_pending"

STAGING_SMOKE=$(python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "hermes-content-studio" / "scripts"))
from lib.research_staging import write_staging, list_pending, approve, format_pending_status
from lib.research_merge import require_approve_on_replace

assert require_approve_on_replace() is True
rid = "smoke-test-run"
brief = Path.home() / "hermes-content-studio" / "content" / "research"
# use tiny fake — approve path copies to live; use unique stamp to avoid clobber
stamp = "2099-01-01"
text = "# smoke\n## Executive Summary\nx\n"
write_staging(run_id=rid, stamp=stamp, mode="replace", keywords="smoke", brief_text=text, insight_count=0)
assert any(i["run_id"] == rid for i in list_pending())
assert "smoke-test-run" in format_pending_status()
# clean without approving to live
import shutil
shutil.rmtree(Path.home() / "hermes-content-studio" / "content" / "research" / "_staging" / rid, ignore_errors=True)
print("OK")
PY
)
[[ "$STAGING_SMOKE" == OK ]] && record PASS "staging_write_list" || record FAIL "staging_write_list"

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
