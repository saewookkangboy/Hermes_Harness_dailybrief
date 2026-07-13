#!/usr/bin/env bash
# Notion OAuth 감시 수동 실행 (상태·알림 시뮬레이션)
# Usage:
#   ./notion-oauth-watch.sh           # 평가 + state 기록
#   ./notion-oauth-watch.sh --check   # 평가만 (state 미기록)
#   ./notion-oauth-watch.sh --json
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_PY="${HERMES_PY:-$HOME/.hermes/hermes-agent/venv/bin/python}"
RECORD=1
JSON=0
for arg in "$@"; do
  case "$arg" in
    --check) RECORD=0 ;;
    --json) JSON=1 ;;
  esac
done

run_py() {
  if [[ -x "$HERMES_PY" ]]; then "$HERMES_PY" "$@"
  else python3 "$@"
  fi
}

run_py - <<PY
import json
import sys
sys.path.insert(0, "$DIR")
from lib.notion_oauth_watch import evaluate_notion_oauth_watch, run_notion_oauth_watch

record = ${RECORD}
if record:
    result = run_notion_oauth_watch(record_state=True)
else:
    result = evaluate_notion_oauth_watch(respect_cooldown=False, try_refresh=True)

payload = {
    "severity": result.severity,
    "code": result.status.code,
    "ok": result.status.ok,
    "detail": result.status.detail,
    "expires_in_hours": result.status.expires_in_hours,
    "should_alert": result.should_alert,
    "refreshed": result.refreshed,
    "refresh_detail": result.refresh_detail,
    "message": result.message,
}
if ${JSON}:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
else:
    print(result.message)
    if result.refresh_detail:
        print(result.refresh_detail)
    print(f"severity={result.severity} alert={result.should_alert}")
raise SystemExit(0 if result.status.ok else 1)
PY
