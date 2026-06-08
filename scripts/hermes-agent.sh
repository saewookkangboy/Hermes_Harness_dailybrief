#!/usr/bin/env bash
# Hermes Conversational Agent — Phase 1 CLI wrapper
# Usage:
#   ./hermes-agent.sh morning
#   ./hermes-agent.sh route "Kurly 인사이트 뭐였지"
#   ./hermes-agent.sh auto "/morning"
#   ./hermes-agent.sh catch-up --days 3
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

if [[ -x "$HERMES_PY" ]]; then
  exec "$HERMES_PY" "$DIR/hermes-agent.py" "$@"
else
  exec python3 "$DIR/hermes-agent.py" "$@"
fi
