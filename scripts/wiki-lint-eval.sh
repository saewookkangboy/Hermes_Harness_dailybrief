#!/usr/bin/env bash
# Wiki 계층 구조 게이트 (네트워크·LLM 불필요)
#
# Usage: ./wiki-lint-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
STAMP="${1:-$(studio_today)}"
REPORT="$WORKDIR/content/logs/${STAMP}_wiki-lint-eval-report.md"
mkdir -p "$WORKDIR/content/logs"

run_py() {
  if [[ -x "$HERMES_PY" ]]; then "$HERMES_PY" "$@"
  else python3 "$@"; fi
}

PASS=0
FAIL=0
RESULT_LINES=()

record() {
  local status="$1" name="$2" detail="$3"
  if [[ "$status" == "PASS" ]]; then PASS=$((PASS + 1)); else FAIL=$((FAIL + 1)); fi
  RESULT_LINES+=("| $status | $name | $detail |")
}

echo "=== Wiki Lint Eval ==="

check_file() {
  local name="$1" path="$2"
  if [[ -f "$WORKDIR/$path" ]]; then
    record PASS "$name" "$path"
  else
    record FAIL "$name" "missing: $path"
  fi
}

check_file "strategy_doc" "docs/LLM-WIKI-INTEGRATION.md"
check_file "wiki_config" "config/wiki.yaml"
check_file "wiki_skill" "skills/shared/wiki-maintainer/SKILL.md"
check_file "wiki_index" "content/wiki/index.md"
check_file "wiki_log" "content/wiki/log.md"
check_dir() {
  local name="$1" path="$2"
  if [[ -d "$WORKDIR/$path" ]]; then
    record PASS "$name" "$path"
  else
    record FAIL "$name" "missing: $path"
  fi
}
check_dir "wiki_concepts" "content/wiki/concepts"
check_dir "research_raw" "content/research/raw"

# memory_router wiki integration
MR=$(run_py -c "
import sys, time
sys.path.insert(0, '$DIR')
from lib.memory_router import route_query
t0 = time.perf_counter()
r = route_query('Claude Anthropic', '$STAMP')
ms = (time.perf_counter() - t0) * 1000
wiki = [h for h in r.hits if h.source.startswith('wiki')]
print(f'wiki_hits={len(wiki)} total={len(r.hits)} ms={ms:.1f}')
" 2>&1)
if echo "$MR" | grep -q "ms="; then
  record PASS "memory_router_wiki" "$(echo "$MR" | tr '\n' ' ')"
else
  record FAIL "memory_router_wiki" "$MR"
fi

# wiki_router unit
WR=$(run_py -c "
import sys
sys.path.insert(0, '$DIR')
from lib.wiki_router import route_wiki
h = route_wiki('anthropic')
print(f'hits={len(h)}')
" 2>&1)
if echo "$WR" | grep -q "hits="; then
  record PASS "wiki_router" "$WR"
else
  record FAIL "wiki_router" "$WR"
fi

{
  echo "# Wiki Lint Eval — $STAMP"
  echo ""
  echo "| Status | Check | Detail |"
  echo "|--------|-------|--------|"
  for line in "${RESULT_LINES[@]}"; do echo "$line"; done
  echo ""
  echo "**Summary:** $PASS PASS / $FAIL FAIL"
} > "$REPORT"

echo ""
echo "📄 $REPORT"
echo "=== $PASS PASS / $FAIL FAIL ==="
[[ "$FAIL" -eq 0 ]]
