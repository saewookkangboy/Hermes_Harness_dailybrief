#!/usr/bin/env bash
# Hermes Studio — 리소스·의존성 MD 생성 → Notion 별도 페이지
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${HOME}/.hermes/hermes-agent/venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi
"$PY" "$DIR/generate-architecture-md.py"
exec "$PY" "$DIR/export-architecture-notion.py" "$@"
