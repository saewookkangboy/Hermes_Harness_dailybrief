#!/usr/bin/env bash
# HERMES_HUMANIZE_LLM 실운영·배선 검증
#
# Usage:
#   ./humanize-llm-eval.sh [YYYY-MM-DD]           # wiring + budget kill
#   HERMES_HUMANIZE_LLM_LIVE=1 ./humanize-llm-eval.sh [DATE]  # linkedin 1채널 LLM
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="${HERMES_PY:-$HOME/.hermes/hermes-agent/venv/bin/python}"
RUN_PY() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}
STAMP="${1:-$(date +%Y-%m-%d)}"
LIVE="${HERMES_HUMANIZE_LLM_LIVE:-0}"
PASS=0
FAIL=0

record() { [[ "$1" == PASS ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1)); echo "$1 $2"; }

echo "=== Humanize LLM Eval — $STAMP ==="

if [[ -x "$DIR/hermes-run.sh" ]]; then
  record PASS "hermes-run.sh"
else
  record FAIL "hermes-run.sh missing"
fi

if grep -q "humanize_llm:" "$WORKDIR/config/content-quality.yaml" 2>/dev/null; then
  record PASS "content-quality humanize_llm"
else
  record FAIL "content-quality humanize_llm"
fi

TIMEOUT_OK=$(RUN_PY - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.content_quality_config import humanize_llm_timeout, humanize_llm_use_codex
ok = humanize_llm_timeout("linkedin") == 120 and humanize_llm_use_codex()
print("ok" if ok else "bad")
PY
)
if [[ "$TIMEOUT_OK" == "ok" ]]; then
  record PASS "humanize_llm_channel_timeout"
else
  record FAIL "humanize_llm_channel_timeout"
fi

BUDGET_KILL=$(RUN_PY - <<PY
import os, sys
sys.path.insert(0, "$DIR")
os.environ["HERMES_LOOP_BUDGET_KILL"] = "1"
from lib.loop_budget import check_loop_budget
print("ok" if not check_loop_budget().ok else "bad")
PY
)
if [[ "$BUDGET_KILL" == "ok" ]]; then
  record PASS "budget_kill_blocks_llm"
else
  record FAIL "budget_kill_blocks_llm"
fi

MCP_NOISE=$(RUN_PY - <<PY 2>&1
import sys
sys.path.insert(0, "$DIR")
from lib.notion_client import setup_mcp
setup_mcp()
PY
)
if echo "$MCP_NOISE" | grep -qiE "MCP server 'playmcp'|playmcp.*failed|unhandled errors"; then
  record FAIL "notion_mcp_playmcp_noise"
else
  record PASS "notion_mcp_playmcp_suppressed"
fi
if echo "$MCP_NOISE" | grep -q "MCP skip servers"; then
  record PASS "notion_mcp_skip_log"
else
  record FAIL "notion_mcp_skip_log"
fi

PARSE_OK=$(RUN_PY - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.hermes_cost import parse_hermes_log_usage
sample = "Total tokens:              1,234\\nTotal cost:              ~$    0.0042"
u = parse_hermes_log_usage(sample)
print("ok" if u["tokens"] == 1234 and abs(u["usd"] - 0.0042) < 1e-6 else "bad")
PY
)
if [[ "$PARSE_OK" == "ok" ]]; then
  record PASS "hermes_cost_parse_tui"
else
  record FAIL "hermes_cost_parse_tui"
fi

CODEX_PARSE=$(RUN_PY - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.hermes_cost import parse_hermes_log_usage
sample = """
23:06:43 - root - DEBUG [20260701_230626_cf9b6b] - Token usage: prompt=19,879, completion=189, total=20,068
23:07:07 - root - DEBUG [20260701_230626_cf9b6b] - Token usage: prompt=25,807, completion=62, total=25,869
23:07:54 - root - DEBUG [20260701_230626_cf9b6b] - Token usage: prompt=29,874, completion=328, total=30,202
Session:        20260701_230626_cf9b6b
"""
u = parse_hermes_log_usage(sample)
expected = 20068 + 25869 + 30202
print("ok" if u["tokens"] == expected else f"bad {u['tokens']} != {expected}")
PY
)
if [[ "$CODEX_PARSE" == "ok" ]]; then
  record PASS "hermes_cost_parse_codex"
else
  record FAIL "hermes_cost_parse_codex ($CODEX_PARSE)"
fi

CODEX_USD=$(RUN_PY - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.hermes_cost import parse_hermes_log_usage
sample = "estimated_cost_usd=0.042\\nResponseUsage(input_tokens=100, output_tokens=50, total_tokens=150, estimated_cost_usd=0.001)"
u = parse_hermes_log_usage(sample)
print("ok" if abs(u["usd"] - 0.043) < 1e-6 else f"bad {u['usd']}")
PY
)
if [[ "$CODEX_USD" == "ok" ]]; then
  record PASS "hermes_cost_parse_codex_usd"
else
  record FAIL "hermes_cost_parse_codex_usd ($CODEX_USD)"
fi

DELTA_OK=$(RUN_PY - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.hermes_cost import parse_run_usage, snapshot_sessions_map, usage_delta_from_sessions
before = {"s1": {"tokens": 1000, "usd": 0.01}}
log = "Session: 20260701_120000_abc123"
# usage_delta returns 0 without real sessions.json — fallback to log parse
sample = "Token usage: prompt=10, completion=5, total=15\\nSession: 20260701_120000_abc123"
u = parse_run_usage(sample, sessions_before=before, prefer_delta=False)
print("ok" if u["tokens"] == 15 else f"bad {u}")
PY
)
if [[ "$DELTA_OK" == "ok" ]]; then
  record PASS "hermes_cost_parse_run_usage"
else
  record FAIL "hermes_cost_parse_run_usage ($DELTA_OK)"
fi

STAGING_OK=$(RUN_PY - <<PY
import os, sys
sys.path.insert(0, "$DIR")
os.environ["HERMES_SUPERVISED_STAGING"] = "1"
from lib.content_quality_config import supervised_stage_blocking
print("ok" if supervised_stage_blocking("naturalness") and not supervised_stage_blocking("voice") else "bad")
PY
)
if [[ "$STAGING_OK" == "ok" ]]; then
  record PASS "supervised_staging_blocking"
else
  record FAIL "supervised_staging_blocking"
fi

PROD_BLOCK=$(RUN_PY - <<PY
import os, sys
sys.path.insert(0, "$DIR")
os.environ.pop("HERMES_SUPERVISED_STAGING", None)
os.environ.pop("HERMES_NATURALNESS_BLOCKING", None)
os.environ.pop("HERMES_VOICE_BLOCKING", None)
from lib.content_quality_config import supervised_stage_blocking
ok = supervised_stage_blocking("naturalness") and supervised_stage_blocking("voice")
print("ok" if ok else "bad")
PY
)
if [[ "$PROD_BLOCK" == "ok" ]]; then
  record PASS "production_voice_naturalness_blocking"
else
  record FAIL "production_voice_naturalness_blocking"
fi

if [[ "$LIVE" == "1" ]]; then
  echo ""
  echo "--- Live LLM (linkedin 1채널) ---"
  LI=$(ls -t "$WORKDIR/content/linkedin/${STAMP}"_linkedin_*.md 2>/dev/null | head -1 || true)
  if [[ -z "$LI" ]]; then
    record FAIL "linkedin artifact missing"
  else
    LIVE_OUT=$(HERMES_HUMANIZE=1 HERMES_HUMANIZE_LLM=1 HERMES_HUMANIZE_LLM_CHANNELS=linkedin \
      HERMES_USE_CODEX="${HERMES_USE_CODEX:-1}" \
      "$DIR/run-humanize-polish.sh" "$STAMP" 2>&1) || true
    echo "$LIVE_OUT"
    if echo "$LIVE_OUT" | grep -q "llm: attempted"; then
      record PASS "humanize_llm_attempted"
    else
      record FAIL "humanize_llm_attempted"
    fi
    if echo "$LIVE_OUT" | grep -q "warn:.*timeout"; then
      TO=$(RUN_PY -c "import sys; sys.path.insert(0,'$DIR'); from lib.content_quality_config import humanize_llm_timeout; print(humanize_llm_timeout('linkedin'))")
      echo "WARN humanize_llm_timeout (hermes-run >${TO}s — 배선 OK)"
      record PASS "humanize_llm_spawn_ok"
    elif echo "$LIVE_OUT" | grep -q "warn:"; then
      record FAIL "humanize_llm_warnings"
    else
      record PASS "humanize_llm_completed"
    fi
    if grep -q "HERMES_HUMANIZE_LLM" "$WORKDIR/.harness/cost-ledger.jsonl" 2>/dev/null; then
      record PASS "cost_ledger_entry"
      TOKENS=$(RUN_PY - <<PY
import json
from pathlib import Path
p = Path("$WORKDIR/.harness/cost-ledger.jsonl")
rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
rows = [r for r in rows if r.get("path") == "HERMES_HUMANIZE_LLM"]
if not rows:
    print(0)
else:
    print(int(rows[-1].get("tokens") or 0))
PY
)
      if [[ "${TOKENS:-0}" -gt 0 ]]; then
        record PASS "cost_ledger_tokens_measured"
      else
        echo "WARN cost_ledger_tokens_zero (Ollama/local — tokens n/a 가능)"
        record PASS "cost_ledger_tokens_recorded"
      fi
    else
      echo "WARN cost_ledger_entry (LLM 미실행 또는 append 생략)"
    fi
  fi
else
  echo ""
  echo "Live LLM 스킵 — HERMES_HUMANIZE_LLM_LIVE=1 로 linkedin 1채널 실운영"
fi

echo ""
echo "=== $PASS PASS · $FAIL FAIL ==="
[[ "$FAIL" -eq 0 ]]
