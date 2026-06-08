#!/usr/bin/env bash
# P4 — CTOR 실측 대시보드 · LinkedIn 팩트체크 해소
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

REPORT="$WORKDIR/content/logs/${STAMP}_newsletter-p4-eval-report.md"
mkdir -p "$WORKDIR/content/logs"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Newsletter P4 Eval — $STAMP ==="

"$DIR/newsletter-p3-eval.sh" "$STAMP" >/dev/null 2>&1 && record PASS "p3_regression" || record FAIL "p3_regression"

LINKEDIN_CTX="$WORKDIR/content/packages/${STAMP}_linkedin-context.md"
[[ -f "$LINKEDIN_CTX" ]] && grep -q 'https://' "$LINKEDIN_CTX" && record PASS "linkedin_has_urls" || record FAIL "linkedin_urls"

python3 <<PY && record PASS "linkedin_fact_check" || record FAIL "linkedin_fact"
import sys
from pathlib import Path
sys.path.insert(0, "${DIR}")
from lib.notion_quality import assess_content
import yaml
cfg = yaml.safe_load((Path.home() / "hermes-content-studio/config/notion-archive.yaml").read_text())
text = Path("${LINKEDIN_CTX}").read_text(encoding="utf-8")
q = assess_content(text, "linkedin", cfg, path=Path("${LINKEDIN_CTX}"))
assert not q.fact_check_issues, q.fact_check_issues
assert q.tier == "canonical", f"tier={q.tier} issues={q.issues}"
PY

"$DIR/newsletter-ctor-record.sh" "$STAMP" --delivered 500 --opens 112 --clicks 14 --notes "p4-eval-seed" >/dev/null \
  && record PASS "ctor_record" || record FAIL "ctor_record"

"$DIR/newsletter-ctor-dashboard.sh" "$STAMP" >/dev/null && record PASS "ctor_dashboard" || record FAIL "ctor_dashboard"

[[ -f "$WORKDIR/content/logs/${STAMP}_newsletter-ctor-dashboard.html" ]] \
  && record PASS "ctor_html_artifact" || record FAIL "ctor_html"

python3 <<PY && record PASS "m4_ctor_kpi" || record FAIL "m4_ctor"
import sys
sys.path.insert(0, "${DIR}")
from lib.m4_analytics import newsletter_kpis
k = newsletter_kpis("${STAMP}")
ctor = k.get("ctor") or {}
assert ctor.get("count", 0) >= 1, ctor
assert ctor.get("latest", {}).get("ctor_pct", 0) > 0
PY

CTOR_HTML="$WORKDIR/content/logs/${STAMP}_newsletter-ctor-dashboard.html"
{
  echo "# Newsletter P4 Eval — $STAMP"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL**"
  echo ""
  echo "## P4 범위"
  echo "- LinkedIn context 출처 URL · 팩트체크 canonical"
  echo "- CTOR 실측 record + dashboard (HTML/MD)"
  echo "- M4 newsletter KPI ctor 블록"
  echo ""
  echo "## 산출물"
  echo "- CTOR Dashboard: $CTOR_HTML"
} > "$REPORT"

echo "Report: $REPORT"
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
