#!/usr/bin/env bash
# Hermes Studio — 리소스·의존성 MD → Notion 별도 페이지
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${HOME}/.hermes/hermes-agent/venv/bin/python"
exec "$PY" "$DIR/export-architecture-notion.py" "$@"
