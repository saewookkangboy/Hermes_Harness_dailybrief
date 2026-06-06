#!/usr/bin/env bash
# Hermes Content Studio — Notion 아카이브 상태 점검
# Usage:
#   ./check-notion-status.sh [YYYY-MM-DD]
#   ./check-notion-status.sh 2026-06-06 --json
#   ./check-notion-status.sh --fix          # 중복 페이지 Draft Archive 이동
#   ./check-notion-status.sh --fix --dry-run
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

ARGS=()
DATE=""
for arg in "$@"; do
  case "$arg" in
    --*) ARGS+=("$arg") ;;
    *)
      if [[ -z "$DATE" ]]; then DATE="$arg"; else ARGS+=("$arg"); fi
      ;;
  esac
done
DATE="${DATE:-$(studio_today)}"

echo "[Notion Status] 점검: $DATE" | tee -a ~/.hermes/logs/content-studio.log

if [[ ${#ARGS[@]} -gt 0 ]]; then
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$DIR/check-notion-status.py" "$DATE" "${ARGS[@]}"
  else
    python3 "$DIR/check-notion-status.py" "$DATE" "${ARGS[@]}"
  fi
else
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$DIR/check-notion-status.py" "$DATE"
  else
    python3 "$DIR/check-notion-status.py" "$DATE"
  fi
fi
