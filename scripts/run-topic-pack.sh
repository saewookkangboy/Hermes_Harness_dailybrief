#!/usr/bin/env bash
# Topic Pack (M1–M6) — 임의 키워드 → 리서치 · AX Blueprint · Resource Map · Future Ahead · 채널 · 아카이브
# Usage:
#   ./run-topic-pack.sh "숏폼 커머스"
#   ./run-topic-pack.sh "RAG 평가" --stages M1,M2,M3,M4
#   ./run-topic-pack.sh "CDP 도입 방법" --notion
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$(cd "$DIR/.." && pwd)}"
export HERMES_WORKDIR="$WORKDIR"

PY="python3"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
if [[ -x "$HERMES_PY" ]] && "$HERMES_PY" -c "import yaml, ddgs" >/dev/null 2>&1; then
  PY="$HERMES_PY"
fi

cd "$WORKDIR"
exec "$PY" "$DIR/run-topic-pack.py" "$@"
