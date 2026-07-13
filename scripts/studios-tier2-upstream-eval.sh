#!/usr/bin/env bash
# Tier 2 upstream integration eval (Personal · Wiki · Dev)
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

[[ -f "$PARENT/content/personal/_inbox_candidates.json" ]] || {
  echo "❌ candidates 없음"
  exit 1
}
[[ -d "$PARENT/content/wiki" ]] || {
  echo "❌ wiki 없음"
  exit 1
}
[[ -f "$PARENT/.harness/feature_list.json" ]] || {
  echo "❌ feature_list 없음"
  exit 1
}

run "personal-pipeline" \
  "HERMES_WORKDIR=$HOME/hermes-personal-studio HERMES_PARENT_STUDIO=$PARENT $HOME/hermes-personal-studio/scripts/run-personal-pipeline.sh $DATE"

run "wiki-pipeline" \
  "HERMES_WORKDIR=$HOME/hermes-wiki-studio HERMES_PARENT_STUDIO=$PARENT $HOME/hermes-wiki-studio/scripts/run-wiki-pipeline.sh $DATE"

run "dev-pipeline" \
  "HERMES_WORKDIR=$HOME/hermes-dev-studio HERMES_PARENT_STUDIO=$PARENT $HOME/hermes-dev-studio/scripts/run-dev-pipeline.sh $DATE"

run "upstream-lib-tier2" \
  "python3 -c \"
import sys
sys.path.insert(0, '$PARENT/scripts')
from pathlib import Path
from lib.studio_upstream import (
    load_inbox_candidates, run_wiki_upstream, load_active_features, load_studio_projects
)
parent = Path('$PARENT')
c = load_inbox_candidates('$DATE', parent)
assert len(c) >= 1
w = run_wiki_upstream(parent, stamp='$DATE', seed=True)
assert w['status']['concepts'] >= 1
f = load_active_features(parent)
assert len(f) >= 1
p = load_studio_projects(parent)
assert len(p) >= 1
print('candidates', len(c), 'concepts', w['status']['concepts'], 'features', len(f), 'projects', len(p))
\""

echo ""
echo "=== tier2-upstream-eval: pass=$PASS fail=$FAIL (date=$DATE) ==="
[[ "$FAIL" -eq 0 ]]
