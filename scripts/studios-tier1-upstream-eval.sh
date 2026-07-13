#!/usr/bin/env bash
# Tier 1 upstream integration eval (Course · Intel · SEO)
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
  echo "❌ brief 없음: $PARENT/content/research/${DATE}_brief.md"
  exit 1
}
BLOG=$(ls "$PARENT/content/blog/${DATE}_blog_"*.html 2>/dev/null | head -1 || true)
[[ -n "$BLOG" ]] || {
  echo "❌ blog 없음: $PARENT/content/blog/${DATE}_blog_*.html"
  exit 1
}

run "course-pipeline" \
  "HERMES_WORKDIR=$HOME/hermes-course-studio HERMES_PARENT_STUDIO=$PARENT $HOME/hermes-course-studio/scripts/run-course-pipeline.sh $DATE"

run "intel-pipeline" \
  "HERMES_WORKDIR=$HOME/hermes-intel-studio HERMES_PARENT_STUDIO=$PARENT $HOME/hermes-intel-studio/scripts/run-intel-pipeline.sh $DATE"

run "seo-pipeline" \
  "HERMES_WORKDIR=$HOME/hermes-seo-studio HERMES_PARENT_STUDIO=$PARENT $HOME/hermes-seo-studio/scripts/run-seo-pipeline.sh $DATE"

run "upstream-lib" \
  "python3 -c \"
import sys
sys.path.insert(0, '$PARENT/scripts')
from lib.studio_upstream import load_brief_insights, load_wiki_concepts, audit_blog_html
from pathlib import Path
assert len(load_brief_insights('$DATE')) >= 7
assert len(load_wiki_concepts()) >= 1
r = audit_blog_html(Path('$BLOG'))
assert r.overall >= 50
print('insights', len(load_brief_insights('$DATE')), 'wiki', len(load_wiki_concepts()), 'seo', r.overall)
\""

echo ""
echo "=== tier1-upstream-eval: pass=$PASS fail=$FAIL (date=$DATE) ==="
[[ "$FAIL" -eq 0 ]]
