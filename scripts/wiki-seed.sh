#!/usr/bin/env bash
# 결정적 Wiki Seed — Brief Graph → content/wiki/concepts (LLM 없음)
#
# Usage:
#   ./wiki-seed.sh
#   HERMES_WIKI_SEED=1 ./run-research-brief.sh  # M1 후 자동 (옵션)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

run_py() {
  if [[ -x "$HERMES_PY" ]]; then "$HERMES_PY" "$@"
  else python3 "$@"; fi
}

cd "$WORKDIR"
OUT=$(PYTHONPATH="$DIR" run_py "$DIR/lib/wiki_seed.py" 2>&1)
echo "$OUT"
COUNT=$(echo "$OUT" | sed -n 's/.*"concepts": \([0-9]*\).*/\1/p' | head -1)
if [[ "${COUNT:-0}" -gt 0 ]]; then
  echo "✅ Wiki Seed: ${COUNT} concepts → content/wiki/concepts/"
else
  echo "⚠️  Wiki Seed: 갱신 없음 (brief_graph 비어 있음)" >&2
  exit 1
fi
