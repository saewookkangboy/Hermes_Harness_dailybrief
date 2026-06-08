#!/usr/bin/env bash
# P2 뉴스레터 통합 eval — config · unified · slack · HITL · Notion
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

REPORT="$WORKDIR/content/logs/${STAMP}_newsletter-p2-eval-report.md"
mkdir -p "$WORKDIR/content/logs"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Newsletter P2 Eval — $STAMP ==="

# Base pipeline eval
"$DIR/newsletter-eval.sh" "$STAMP" >/dev/null 2>&1 && record PASS "newsletter-eval base" || record FAIL "newsletter-eval base"

UNIFIED="$WORKDIR/content/packages/${STAMP}_unified-context.md"
grep -q "## Newsletter (B2B 이메일)" "$UNIFIED" 2>/dev/null && record PASS "unified_newsletter_section" || record FAIL "unified_section"
grep -q "권장 제목" "$UNIFIED" 2>/dev/null && record PASS "unified_winner_title" || record FAIL "unified_winner"

python3 <<PY 2>/dev/null && record PASS "config_loader_wired" || record FAIL "config_loader"
import sys
sys.path.insert(0, "${DIR}")
from lib.newsletter_quality import load_newsletter_config, _subject_candidates
cfg = load_newsletter_config()
assert cfg.get("subject_templates"), "subject_templates missing"
subs = _subject_candidates("테스트 토픽", "${STAMP}", cfg)
assert subs and all(len(s) <= 50 for s in subs), subs
PY

python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.publish_gate import VALID_CHANNELS
assert 'newsletter' in VALID_CHANNELS
" 2>/dev/null && record PASS "publish_gate_newsletter" || record FAIL "publish_gate"

[[ -f "$WORKDIR/skills/channels/newsletter/SKILL.md" ]] && record PASS "newsletter_skill" || record FAIL "skill"

SKIP_INIT=1 "$DIR/slack-daily-log.sh" "$STAMP" --build-only >/dev/null 2>&1
DIGEST="$WORKDIR/content/logs/${STAMP}_daily-slack-digest.md"
if [[ -n "$DIGEST" ]] && grep -qi "newsletter" "$DIGEST" 2>/dev/null; then
  record PASS "slack_digest_newsletter"
else
  # digest may use section headers
  if [[ -n "$DIGEST" ]] && grep -qi "Newsletter" "$DIGEST" 2>/dev/null; then
    record PASS "slack_digest_newsletter"
  else
    record FAIL "slack_digest"
  fi
fi

"$DIR/validate-output.sh" unified-context "$UNIFIED" >/dev/null 2>&1 && record PASS "validate_unified" || record FAIL "validate_unified"
"$DIR/validate-output.sh" unified-newsletter "$UNIFIED" >/dev/null 2>&1 && record PASS "validate_unified_patch" || record FAIL "validate_unified_patch"

{
  echo "# Newsletter P2 Eval — $STAMP"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL**"
  echo ""
  echo "## P2 범위"
  echo "- newsletter.yaml 로더 연동"
  echo "- unified-context Newsletter 블록"
  echo "- slack-daily-log · publish_gate · skill"
} > "$REPORT"

echo "Report: $REPORT"
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
