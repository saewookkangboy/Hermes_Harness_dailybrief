#!/usr/bin/env bash
# B2B 뉴스레터 생성 — Brief SoT → newsletter.md + context (결정적)
#
# Usage:
#   ./run-newsletter.sh [YYYY-MM-DD]
#   ./run-newsletter.sh 2026-06-08 --validate
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
VALIDATE=0
[[ "${2:-}" == "--validate" ]] && VALIDATE=1

run_py() {
  if [[ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]]; then
    "$HOME/.hermes/hermes-agent/venv/bin/python" "$@"
  else
    python3 "$@"
  fi
}

NL_START=$(date +%s)
_ASSEMBLE_OUT=$(run_py "$DIR/assemble-newsletter.py" "$STAMP" 2>/dev/null)
NL_ELAPSED=$(( $(date +%s) - NL_START ))
NL=$(echo "$_ASSEMBLE_OUT" | sed -n '1p')
CTX=$(echo "$_ASSEMBLE_OUT" | sed -n '2p')
HTML=$(echo "$_ASSEMBLE_OUT" | sed -n '3p')
PASTE=$(echo "$_ASSEMBLE_OUT" | sed -n '4p')
SCORES="$WORKDIR/content/newsletter/${STAMP}_newsletter_subject-scores.json"
echo "✅ Newsletter · $STAMP"
echo "📄 $NL"
echo "📦 $CTX"
echo "📧 $HTML"
echo "📋 $PASTE"
[[ -f "$SCORES" ]] && echo "📊 $SCORES"

if [[ "$VALIDATE" -eq 1 ]]; then
  "$DIR/validate-output.sh" newsletter "$NL"
  "$DIR/validate-output.sh" newsletter-context "$CTX"
  "$DIR/validate-output.sh" newsletter-html "$HTML"
  "$DIR/validate-output.sh" newsletter-paste "$PASTE"
  "$DIR/validate-output.sh" newsletter-subject-scores "$SCORES"
  UNIFIED="$WORKDIR/content/packages/${STAMP}_unified-context.md"
  [[ -f "$UNIFIED" ]] && "$DIR/validate-output.sh" unified-newsletter "$UNIFIED"
fi

HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
if [[ -x "$HERMES_PY" ]]; then
  "$HERMES_PY" -c "
import sys
sys.path.insert(0, '$DIR/lib')
from harness import append_trace, check_regression
r = check_regression('newsletter', $NL_ELAPSED)
append_trace({'stage': 'newsletter', 'elapsed_seconds': $NL_ELAPSED, 'date': '$STAMP', **r})
" 2>/dev/null || true
fi
