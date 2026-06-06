#!/usr/bin/env bash
# Hermes claude-design 스킬로 강의 HTML 덱 polish
# Usage: polish-lecture-claude-design.sh TOPIC STAMP OUTLINE BASE_HTML OUTPUT_HTML PPTX
set -euo pipefail

TOPIC="${1:?topic}"
STAMP="${2:?stamp}"
OUTLINE="${3:?outline path}"
BASE_HTML="${4:?base html path}"
OUTPUT_HTML="${5:?output html path}"
PPTX="${6:?pptx path}"
PRESET="${7:-claude}"

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
SCRIPTS="$WORKDIR/scripts"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

run_python() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

PROMPT=$(run_python "$SCRIPTS/build-claude-design-prompt.py" \
  --topic "$TOPIC" \
  --stamp "$STAMP" \
  --outline "$OUTLINE" \
  --base-html "$BASE_HTML" \
  --output-html "$OUTPUT_HTML" \
  --pptx "$PPTX" \
  --preset "$PRESET")

echo "=== claude-design HTML 덱 (Hermes) ===" >&2
echo "출력: $OUTPUT_HTML" >&2

export HERMES_TOOLSETS=hermes-cli
export HERMES_USE_CODEX=1
"$SCRIPTS/hermes-run.sh" "$PROMPT" \
  --skills claude-design,content-studio-slides \
  -t hermes-cli

if [[ ! -f "$OUTPUT_HTML" ]]; then
  echo "⚠️  claude-design HTML 미생성 — base HTML 복원" >&2
  cp "$BASE_HTML" "$OUTPUT_HTML"
  exit 1
fi

echo "✅ claude-design HTML: $OUTPUT_HTML"
