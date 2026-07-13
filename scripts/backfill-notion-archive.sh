#!/usr/bin/env bash
# 미동기화 일자 Notion archive 백필 (OAuth preflight 필수)
#
# Usage:
#   ./backfill-notion-archive.sh 2026-07-06 2026-07-09
#   ./backfill-notion-archive.sh 2026-07-06 2026-07-06 --dry-run
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="${HERMES_PY:-$HOME/.hermes/hermes-agent/venv/bin/python}"
DRY_RUN=0

FROM="${1:-}"
TO="${2:-$FROM}"
shift 2 2>/dev/null || true
for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=1
done

if [[ -z "$FROM" ]]; then
  echo "Usage: $0 FROM_DATE [TO_DATE] [--dry-run]" >&2
  exit 1
fi

echo "=== Notion Archive Backfill: $FROM → $TO ==="

"$HERMES_PY" - <<PY
import sys
sys.path.insert(0, "$DIR")
from lib.notion_oauth import check_notion_oauth_status, format_oauth_alert

status = check_notion_oauth_status()
if not status.ok:
    print(format_oauth_alert(status))
    print("먼저: $DIR/reauth-notion-mcp.sh")
    raise SystemExit(2)
print(status.detail)
PY

current="$FROM"
end="$TO"
fail=0
ok=0

while [[ "$current" < "$end" || "$current" == "$end" ]]; do
  brief="$WORKDIR/content/research/${current}_brief.md"
  if [[ ! -f "$brief" ]]; then
    echo "⏭ $current — brief 없음"
    current=$(date -j -v+1d -f "%Y-%m-%d" "$current" +%Y-%m-%d 2>/dev/null || date -d "$current + 1 day" +%Y-%m-%d)
    continue
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "DRY $current — archive-to-notion.sh --force"
    ok=$((ok + 1))
  elif "$DIR/archive-to-notion.sh" "$current" --force; then
    echo "✅ $current"
    ok=$((ok + 1))
  else
    echo "❌ $current"
    fail=$((fail + 1))
  fi
  current=$(date -j -v+1d -f "%Y-%m-%d" "$current" +%Y-%m-%d 2>/dev/null || date -d "$current + 1 day" +%Y-%m-%d)
done

echo ""
echo "=== backfill 완료: ok=$ok fail=$fail ==="
[[ "$fail" -eq 0 ]]
