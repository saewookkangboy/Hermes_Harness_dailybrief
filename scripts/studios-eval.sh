#!/usr/bin/env bash
# Validate all Hermes sibling studios (struct + pipeline smoke)
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
DATE="${1:-$(date +%F)}"
PASS=0
FAIL=0

check() {
  local id="$1"
  local root="$HOME/hermes-${id}-studio"
  echo "--- $id ($root) ---"
  if [[ ! -d "$root" ]]; then
    echo "❌ missing: $root"
    FAIL=$((FAIL + 1))
    return
  fi
  if HERMES_WORKDIR="$root" "$root/scripts/harness-eval.sh" --quick; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    return
  fi
  if HERMES_WORKDIR="$root" "$root/scripts/run-${id}-pipeline.sh" "$DATE"; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
  fi
}

for id in course intel seo personal wiki dev delivery social; do
  check "$id"
done

echo ""
echo "=== studios-eval: pass=$PASS fail=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
