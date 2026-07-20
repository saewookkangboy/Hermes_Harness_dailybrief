#!/usr/bin/env bash
# Hermes Content Studio — 일일 리서치 브리프 (Top 7) · Brief SoT
#
# gather(일일 최신) → assemble → validate
# HERMES_RESEARCH_KEYWORDS set → run-keyword-research.py (merge/replace/staging)
# HERMES_ENHANCE=1: assemble 후 Hermes polish (선택)
#
# Usage: ./run-research-brief.sh [YYYY-MM-DD]
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
SCRIPTS="$WORKDIR/scripts"
# shellcheck source=lib/studio-date.sh
source "$SCRIPTS/lib/studio-date.sh"
DATE="${1:-$(studio_today)}"
OUTPUT="$WORKDIR/content/research/${DATE}_brief.md"
SEARCH_JSON="$WORKDIR/content/research/_search_context_${DATE}.json"
SEARCH_MD="$WORKDIR/content/research/_search_context_${DATE}.md"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

cd "$WORKDIR"
mkdir -p content/research

run_python() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

if [[ -n "${HERMES_RESEARCH_KEYWORDS:-}" ]]; then
  echo "=== Keyword research (merge/replace/staging) ==="
  run_python "$SCRIPTS/run-keyword-research.py" "$DATE"
  if [[ -f "$OUTPUT" ]]; then
    echo "📄 Brief SoT: $OUTPUT"
  fi
  echo "📎 Search: $SEARCH_JSON"
  exit 0
fi

echo "=== 1/3 일일 웹 검색 수집 (Brief SoT) ==="
run_python "$SCRIPTS/gather-web-research.py" "$DATE"
[[ -f "$SEARCH_JSON" ]] || { echo "❌ 검색 컨텍스트 없음: $SEARCH_JSON" >&2; exit 1; }

echo ""
echo "=== 2/3 브리프 조립 Top 7 (assemble-research-brief.py) ==="
run_python "$SCRIPTS/assemble-research-brief.py" "$DATE"
[[ -f "$OUTPUT" ]] || { echo "❌ brief 생성 실패" >&2; exit 1; }

if [[ "${HERMES_ENHANCE:-0}" == "1" ]]; then
  echo ""
  echo "=== 2b/3 Hermes polish (선택) ==="
  HERMES_TOOLSETS=hermes-cli HERMES_USE_CODEX=1 "$SCRIPTS/hermes-run.sh" \
    "read_file ${OUTPUT} 와 ${SEARCH_MD} 참조. ${OUTPUT} 내용을 marketing-research 형식에 맞게 다듬되 구조 유지. write_file로 저장." \
    --skills marketing-research -t hermes-cli || echo "⚠️  Hermes polish skip"
fi

echo ""
echo "=== 3/3 Brief 품질 검증 ==="
"$SCRIPTS/validate-output.sh" research "$OUTPUT"
echo ""
echo "📄 Brief SoT: $OUTPUT"
echo "📎 Search: $SEARCH_JSON"
