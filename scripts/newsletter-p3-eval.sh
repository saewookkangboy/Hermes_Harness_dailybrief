#!/usr/bin/env bash
# P3 뉴스레터 마감 eval — Notion 동기화 · M4 KPI · 문서·registry
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

REPORT="$WORKDIR/content/logs/${STAMP}_newsletter-p3-eval-report.md"
mkdir -p "$WORKDIR/content/logs"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Newsletter P3 Eval — $STAMP ==="

"$DIR/newsletter-p2-eval.sh" "$STAMP" >/dev/null 2>&1 && record PASS "p2_regression" || record FAIL "p2_regression"

python3 <<PY && record PASS "notion_newsletter_synced" || record FAIL "notion_sync"
import json
from pathlib import Path
stamp = "${STAMP}"
state = json.loads((Path.home() / "hermes-content-studio/content/.notion-archive-state.json").read_text())
pages = state.get("pages") or {}
for cat in ("newsletter", "newsletter_html"):
    meta = pages.get(f"{stamp}/{cat}")
    assert meta and meta.get("tier") == "canonical", f"{cat} not canonical: {meta}"
    assert meta.get("url"), f"{cat} no url"
PY

python3 <<PY && record PASS "m4_newsletter_kpis" || record FAIL "m4_kpis"
import sys
sys.path.insert(0, "${DIR}")
from lib.m4_analytics import newsletter_kpis, build_m4_report
k = newsletter_kpis("${STAMP}")
assert k.get("scores_available"), k
assert k.get("winner_score", 0) >= 40
r = build_m4_report(7, stamp="${STAMP}")
assert r.get("newsletter")
PY

[[ -f "$WORKDIR/README.md" ]] && grep -q "newsletter" "$WORKDIR/README.md" && record PASS "readme_newsletter" || record FAIL "readme"
[[ -f "$WORKDIR/HARNESS.md" ]] && grep -q "newsletter" "$WORKDIR/HARNESS.md" && record PASS "harness_md_newsletter" || record FAIL "harness_md"
jq -e '.features[] | select(.id=="pipe-008") | .verification[] | select(test("newsletter-p2"))' \
  "$WORKDIR/.harness/feature_list.json" >/dev/null 2>&1 && record PASS "feature_pipe008_p2" || record FAIL "feature_list"

NL_URL=$(python3 -c "import json; s=json.load(open('$WORKDIR/content/.notion-archive-state.json')); print(s['pages']['$STAMP/newsletter']['url'])")
HTML_URL=$(python3 -c "import json; s=json.load(open('$WORKDIR/content/.notion-archive-state.json')); print(s['pages']['$STAMP/newsletter_html']['url'])")

{
  echo "# Newsletter P3 Eval — $STAMP"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL**"
  echo ""
  echo "## Notion Permalink"
  echo "- Newsletter: $NL_URL"
  echo "- Newsletter HTML: $HTML_URL"
  echo ""
  echo "## P3 범위"
  echo "- Notion 동기화 검증 · M4 KPI · README/HARNESS · feature_list"
} > "$REPORT"

echo "Report: $REPORT"
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
