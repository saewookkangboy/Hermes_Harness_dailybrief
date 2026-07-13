#!/usr/bin/env bash
# All studio upstream evals (Tier 1 + 2 + 3)
set -euo pipefail
DATE="${1:-2026-07-12}"
DIR="$(cd "$(dirname "$0")" && pwd)"
FAIL=0

for script in studios-tier1-upstream-eval.sh studios-tier2-upstream-eval.sh studios-tier3-upstream-eval.sh; do
  echo "======== $script ========"
  if ! "$DIR/$script" "$DATE"; then
    FAIL=$((FAIL + 1))
  fi
  echo ""
done

echo "=== studios-all-upstream-eval: tier_failures=$FAIL (date=$DATE) ==="
[[ "$FAIL" -eq 0 ]]
