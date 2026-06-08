#!/usr/bin/env bash
# 뉴스레터 파이프라인 eval + 리포트 (HTML · A/B 스코어 · Notion 설정)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

REPORT="$WORKDIR/content/logs/${STAMP}_newsletter-eval-report.md"
mkdir -p "$WORKDIR/content/logs"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Newsletter Eval — $STAMP ==="
T0=$(date +%s)
GEN=$("$DIR/run-newsletter.sh" "$STAMP" --validate 2>&1)
ELAPSED=$(( $(date +%s) - T0 ))
NL=$(ls -1 "$WORKDIR/content/newsletter/${STAMP}"_newsletter_*.md 2>/dev/null | head -1)
HTML=$(ls -1 "$WORKDIR/content/newsletter/${STAMP}"_newsletter_*.html 2>/dev/null | head -1)
CTX="$WORKDIR/content/packages/${STAMP}_newsletter-context.md"
SCORES="$WORKDIR/content/newsletter/${STAMP}_newsletter_subject-scores.json"

[[ -f "$NL" ]] && record PASS "assemble ${ELAPSED}s" || record FAIL "assemble"
grep -q "## 30초 TLDR" "$NL" 2>/dev/null && record PASS "tldr_module" || record FAIL "tldr"
grep -q "이번 주 실습 1가지" "$NL" 2>/dev/null && record PASS "single_cta" || record FAIL "cta"
grep -q "자동 스코어" "$NL" 2>/dev/null && record PASS "subject_ab_score" || record FAIL "subject_score"
grep -q "권장 제목" "$NL" 2>/dev/null && record PASS "subject_winner" || record FAIL "subject_winner"
[[ -f "$HTML" ]] && record PASS "html_email" || record FAIL "html"
[[ -f "$SCORES" ]] && record PASS "subject_json" || record FAIL "subject_json"
[[ -f "$CTX" ]] && record PASS "context_package" || record FAIL "context"
grep -q "newsletter:" "$WORKDIR/config/notion-archive.yaml" 2>/dev/null && record PASS "notion_category" || record FAIL "notion"

SAMPLE=$(head -60 "$NL" 2>/dev/null || echo "N/A")
WINNER=$(python3 -c "import json; d=json.load(open('$SCORES')); print(d.get('winner',{}).get('text','N/A')+' (score '+str(d.get('winner',{}).get('score','?'))+')')" 2>/dev/null || echo "N/A")
{
  echo "# Newsletter Eval — $STAMP"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL** · ${ELAPSED}s"
  echo ""
  echo "## 신규 기능"
  echo "- A/B 제목 자동 스코어링 → \`subject-scores.json\`"
  echo "- HTML 이메일 템플릿 → \`templates/email/newsletter.html\`"
  echo "- Notion 아카이브: \`newsletter\` + \`newsletter_html\` 카테고리"
  echo ""
  echo "## 권장 제목"
  echo "\`$WINNER\`"
  echo ""
  echo "## 구조 근거"
  echo "- Stripo B2B 2026: CTOR 10–15%, 제목 ≤50자"
  echo "- Morning Brew: TLDR → 모듈 → 단일 CTA"
  echo "- Dyspatch: 재사용 모듈형 블록"
  echo ""
  echo "## 샘플 (코드복사)"
  echo '```'
  echo "$SAMPLE"
  echo '```'
} > "$REPORT"
echo "Report: $REPORT"
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
