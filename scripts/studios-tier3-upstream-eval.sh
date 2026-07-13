#!/usr/bin/env bash
# Tier 3 upstream integration eval (Delivery · Social)
set -euo pipefail
DATE="${1:-2026-07-12}"
PARENT="${HERMES_PARENT_STUDIO:-$HOME/hermes-content-studio}"
PASS=0
FAIL=0

run() {
  local name="$1" cmd="$2"
  echo "--- $name ---"
  if eval "$cmd"; then
    PASS=$((PASS + 1))
    echo "✅ $name"
  else
    FAIL=$((FAIL + 1))
    echo "❌ $name"
  fi
}

[[ -f "$PARENT/content/research/${DATE}_brief.md" ]] || {
  echo "❌ brief 없음"
  exit 1
}
POST=$(ls "$PARENT/content/linkedin/${DATE}_linkedin_"*.md 2>/dev/null | head -1 || true)
[[ -n "$POST" ]] || {
  echo "❌ linkedin 없음"
  exit 1
}

run "delivery-pipeline" \
  "HERMES_WORKDIR=$HOME/hermes-delivery-studio HERMES_PARENT_STUDIO=$PARENT $HOME/hermes-delivery-studio/scripts/run-delivery-pipeline.sh $DATE"

run "social-pipeline" \
  "HERMES_WORKDIR=$HOME/hermes-social-studio HERMES_PARENT_STUDIO=$PARENT $HOME/hermes-social-studio/scripts/run-social-pipeline.sh $DATE"

run "upstream-lib-tier3" \
  "python3 -c \"
import sys
sys.path.insert(0, '$PARENT/scripts')
from pathlib import Path
from lib.studio_upstream import (
    load_content_calendar, find_linkedin_post, parse_linkedin_post, delivery_insights, load_brief_insights
)
parent = Path('$PARENT')
cal = load_content_calendar('$DATE', parent)
assert len(cal) >= 1
post = find_linkedin_post('$DATE', parent)
assert post is not None
parsed = parse_linkedin_post(post.read_text(encoding='utf-8'))
assert parsed['hook']
insights = delivery_insights(load_brief_insights('$DATE', parent))
assert len(insights) >= 1
print('calendar', len(cal), 'hook', parsed['hook'][:40], 'insights', len(insights))
\""

echo ""
echo "=== tier3-upstream-eval: pass=$PASS fail=$FAIL (date=$DATE) ==="
[[ "$FAIL" -eq 0 ]]
