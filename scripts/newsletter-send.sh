#!/usr/bin/env bash
# 뉴스레터 ESP 발송 — dry-run 기본 · --live는 HITL + RESEND_API_KEY
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="${1:-$(date +%Y-%m-%d)}"
LIVE=0
APPROVE=0
TO=""

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --live) LIVE=1 ;;
    --approve) APPROVE=1 ;;
    --to) TO="${2:-}"; shift ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
  shift
done

[[ "$APPROVE" -eq 1 ]] && export HERMES_ESP_APPROVED=1

run_py() {
  if [[ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]]; then
    "$HOME/.hermes/hermes-agent/venv/bin/python" "$@"
  else
    python3 "$@"
  fi
}

if [[ "$LIVE" -eq 1 && "${HERMES_ESP_APPROVED:-0}" != "1" ]]; then
  echo "❌ ESP live 발송은 HITL 승인 필요" >&2
  echo "   hermes-agent.sh approve esp --date $STAMP" >&2
  exit 1
fi

run_py "$DIR/_newsletter_send_cli.py" "$STAMP" "$LIVE" "$TO"
