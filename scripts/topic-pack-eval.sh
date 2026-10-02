#!/usr/bin/env bash
# Topic Pack (M1–M6) eval — 오프라인 fixture 기반 (네트워크 불필요)
# Usage: ./topic-pack-eval.sh [--live "키워드"]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$(cd "$DIR/.." && pwd)}"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

LIVE_KW=""
[[ "${1:-}" == "--live" ]] && LIVE_KW="${2:-숏폼 커머스}"

PY="python3"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
if [[ -x "$HERMES_PY" ]] && "$HERMES_PY" -c "import yaml, pytest" >/dev/null 2>&1; then
  PY="$HERMES_PY"
fi

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
export HERMES_TOPICS_ROOT="$TMP_ROOT/topics"
export HERMES_TOPIC_FEEDBACK="$TMP_ROOT/lens-feedback.json"
export HERMES_TOPIC_TRACE=0

echo "=== Topic Pack (M1–M6) Eval ==="

for f in config/topic-research.yaml scripts/run-topic-pack.sh scripts/run-topic-pack.py \
         scripts/lib/ax/pipeline.py tests/fixtures/topic/short-form-commerce.json; do
  [[ -f "$WORKDIR/$f" ]] && record PASS "file:$f" || record FAIL "file:$f"
done

grep -q "qc topic" "$WORKDIR/config/telegram-routing.yaml" && record PASS "telegram_routing" || record FAIL "telegram_routing"
grep -q "qc topic" "$WORKDIR/config/slack-routing.yaml" && record PASS "slack_routing" || record FAIL "slack_routing"
grep -q "qc topic" "$WORKDIR/config/playmcp-routing.yaml" && record PASS "playmcp_routing" || record FAIL "playmcp_routing"
grep -q '"/topic"' "$WORKDIR/config/agent-commands.yaml" && record PASS "agent_commands" || record FAIL "agent_commands"
grep -q "topic_pack:" "$WORKDIR/config/notion-archive.yaml" && record PASS "notion_category" || record FAIL "notion_category"
bash -n "$DIR/telegram-pipeline.sh" && record PASS "telegram_pipeline_syntax" || record FAIL "telegram_pipeline_syntax"

if ! grep -q "enterprise AI" "$WORKDIR/scripts/run-keyword-research.py"; then
  record PASS "no_hardcoded_enterprise_ai"
else
  record FAIL "no_hardcoded_enterprise_ai"
fi

if (cd "$WORKDIR" && "$PY" -m pytest -q tests/test_ax_*.py >"$TMP_ROOT/pytest.log" 2>&1); then
  record PASS "pytest_ax ($(tail -1 "$TMP_ROOT/pytest.log"))"
else
  record FAIL "pytest_ax"; tail -20 "$TMP_ROOT/pytest.log"
fi

STAMP="2099-01-01"
if (cd "$WORKDIR" && "$DIR/run-topic-pack.sh" "숏폼 커머스" --date "$STAMP" \
      --fixture tests/fixtures/topic/short-form-commerce.json --json >"$TMP_ROOT/e2e.json" 2>"$TMP_ROOT/e2e.err"); then
  record PASS "fixture_e2e_all_gates"
else
  record FAIL "fixture_e2e_all_gates"; tail -20 "$TMP_ROOT/e2e.err"
fi

SLUG_DIR="$HERMES_TOPICS_ROOT/short-form-video-commerce"
for pair in "topic-brief:research" "ax-blueprint:ax-blueprint" "resource-map:resource-map" \
            "future-ahead:future-ahead" "topic-pack:topic-pack"; do
  vtype="${pair%%:*}"; kind="${pair##*:}"
  file="$SLUG_DIR/${STAMP}_${kind}_short-form-video-commerce.md"
  if [[ -f "$file" ]] && "$DIR/validate-output.sh" "$vtype" "$file" >/dev/null 2>&1; then
    record PASS "validate:$vtype"
  else
    record FAIL "validate:$vtype"
  fi
done

[[ -f "$HERMES_TOPICS_ROOT/_index.json" ]] && record PASS "topic_index" || record FAIL "topic_index"

if "$PY" - "$TMP_ROOT/e2e.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
assert s["passed"] is True, s
assert s["domain_id"] == "commerce", s["domain_id"]
assert s["slug"] == "short-form-video-commerce", s["slug"]
assert not s.get("stopped_at")
PY
then record PASS "summary_json"; else record FAIL "summary_json"; fi

if [[ -n "$LIVE_KW" ]]; then
  if (cd "$WORKDIR" && "$DIR/run-topic-pack.sh" "$LIVE_KW" --date "$STAMP" --json >"$TMP_ROOT/live.json" 2>"$TMP_ROOT/live.err"); then
    record PASS "live_e2e:$LIVE_KW"
  else
    record FAIL "live_e2e:$LIVE_KW"; tail -20 "$TMP_ROOT/live.err"
  fi
fi

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
