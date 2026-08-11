#!/usr/bin/env bash
# Slack Cursor handoff — routing · entry · dual-notify smoke
# Usage: ./slack-cursor-handoff-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$(cd "$DIR/.." && pwd)}"
pass=0
fail=0
ok() { echo "PASS: $*"; pass=$((pass + 1)); }
bad() { echo "FAIL: $*"; fail=$((fail + 1)); }

echo "=== Slack Cursor Handoff Eval ==="
echo "WORKDIR=$WORKDIR"

if grep -q 'load_slack_channel' "$DIR/run-cursor-handoff.sh" \
  && grep -q 'slack-notify.sh' "$DIR/run-cursor-handoff.sh"; then
  ok "run-cursor-handoff dual notify hooks"
else
  bad "run-cursor-handoff dual notify hooks"
fi

if [[ -x "$DIR/cursor-handoff.sh" ]]; then
  ok "cursor-handoff.sh executable"
else
  bad "cursor-handoff.sh executable"
fi

if bash -n "$DIR/cursor-handoff.sh" 2>/dev/null; then
  ok "cursor-handoff.sh bash -n"
else
  bad "cursor-handoff.sh bash -n"
fi

if bash -n "$DIR/run-cursor-handoff.sh" 2>/dev/null; then
  ok "run-cursor-handoff.sh bash -n"
else
  bad "run-cursor-handoff.sh bash -n"
fi

ROUTING="$WORKDIR/config/slack-routing.yaml"
if grep -qE '^[[:space:]]*cursor:' "$ROUTING" \
  && grep -q 'cursor-handoff.sh' "$ROUTING"; then
  ok "slack-routing has /cursor → cursor-handoff.sh"
else
  bad "slack-routing has /cursor → cursor-handoff.sh"
fi

if grep -qE '^[[:space:]]*automate:' "$ROUTING" \
  && grep -A2 -E '^[[:space:]]*automate:' "$ROUTING" | grep -q 'personal-assistant'; then
  ok "/automate still personal-assistant alias"
else
  bad "/automate still personal-assistant alias"
fi

if grep -qE '^[[:space:]]*handoff:' "$ROUTING" \
  && grep -A2 -E '^[[:space:]]*handoff:' "$ROUTING" | grep -q 'qc handoff'; then
  ok "/handoff still session qc handoff"
else
  bad "/handoff still session qc handoff"
fi

# dry-run: OK if HANDOFF exists; acceptable exit 1 if none
set +e
DRY_OUT=$("$DIR/run-cursor-handoff.sh" --dry-run --latest 2>&1)
DRY_EC=$?
set -e
if [[ "$DRY_EC" -eq 0 ]] && echo "$DRY_OUT" | grep -q 'handoff:'; then
  ok "run-cursor-handoff --dry-run --latest"
elif echo "$DRY_OUT" | grep -q 'HANDOFF 없음'; then
  ok "run-cursor-handoff --dry-run (no HANDOFF yet — expected)"
else
  bad "run-cursor-handoff --dry-run unexpected ec=$DRY_EC"
  echo "$DRY_OUT" | head -20
fi

# usage smoke
if "$DIR/cursor-handoff.sh" --help 2>&1 | grep -qi cursor; then
  ok "cursor-handoff --help"
else
  bad "cursor-handoff --help"
fi

echo ""
echo "=== $pass PASS · $fail FAIL ==="
[[ "$fail" -eq 0 ]]
