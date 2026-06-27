#!/usr/bin/env bash
# 우선순위 P1–P8 기능 통합 eval (결정적)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Features Priority Eval P1–P8 — $STAMP ==="

# P1 CTOR feedback
python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.newsletter_ctor_feedback import compute_ctor_feedback, apply_ctor_feedback_bonus
fb = compute_ctor_feedback()
assert 'weights' in fb
b, r = apply_ctor_feedback_bonus('AX 실무, 3분이면 돼요?')
print('ok', b)
" 2>/dev/null && record PASS "p1_ctor_feedback" || record FAIL "p1_ctor_feedback"

# P2 HITL newsletter
grep -q "newsletter" "$WORKDIR/config/agent-commands.yaml" && record PASS "p2_publish_newsletter_yaml" || record FAIL "p2_yaml"
python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.publish_gate import VALID_CHANNELS
assert 'newsletter' in VALID_CHANNELS
" 2>/dev/null && record PASS "p2_publish_gate" || record FAIL "p2_publish_gate"

# P3 Wiki → M2
python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.wiki_concepts import inject_wiki_blurbs
from lib.content_quality import Insight
ins = Insight(title='AX test', summary='s', marketer_view='v', channels='blog', url='http://x')
inject_wiki_blurbs([ins])
" 2>/dev/null && record PASS "p3_wiki_inject" || record FAIL "p3_wiki_inject"

# P4 Proactive + weekly digest
python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.proactive_triggers import run_proactive_checks
from lib.brief_graph import format_weekly_digest
run_proactive_checks('$STAMP')
format_weekly_digest(14)
" 2>/dev/null && record PASS "p4_proactive_weekly" || record FAIL "p4_proactive_weekly"
[[ -x "$DIR/cron-weekly-graph-digest.sh" ]] && record PASS "p4_cron_weekly" || record FAIL "p4_cron_weekly"

# P5 Blog M3
[[ -x "$DIR/run-blog-pipeline.sh" ]] && record PASS "p5_blog_script" || record FAIL "p5_blog_script"
python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.blog_pipeline import run_blog_pipeline
" 2>/dev/null && record PASS "p5_blog_module" || record FAIL "p5_blog_module"

# P6 M4 live metrics
python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.m4_channel_metrics import m4_analytics_mode, sync_ctor_to_channel_metrics
sync_ctor_to_channel_metrics()
print(m4_analytics_mode())
" 2>/dev/null && record PASS "p6_m4_metrics" || record FAIL "p6_m4_metrics"

# P7 PlayMCP
[[ -f "$WORKDIR/config/playmcp-routing.yaml" ]] && record PASS "p7_playmcp_yaml" || record FAIL "p7_playmcp_yaml"
[[ -x "$DIR/setup-playmcp-routing.sh" ]] && record PASS "p7_playmcp_setup" || record FAIL "p7_playmcp_setup"

# P8 ESP controlled live
[[ -x "$DIR/newsletter-send.sh" ]] && record PASS "p8_esp_script" || record FAIL "p8_esp_script"
python3 -c "
import sys
sys.path.insert(0, '$DIR')
from lib.newsletter_esp import build_send_manifest
" 2>/dev/null && record PASS "p8_esp_module" || record FAIL "p8_esp_module"

echo ""
echo "PASS: $PASS · FAIL: $FAIL"
[[ "$FAIL" -eq 0 ]]
