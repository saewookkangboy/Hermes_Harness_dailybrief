#!/usr/bin/env bash
# P6 — Notion 붙여넣기 팩 (ESP 발송 없음)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

REPORT="$WORKDIR/content/logs/${STAMP}_newsletter-p6-eval-report.md"
PASTE="$WORKDIR/content/packages/${STAMP}_newsletter-paste.md"
mkdir -p "$WORKDIR/content/logs"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Newsletter P6 Eval — $STAMP ==="

"$DIR/run-newsletter.sh" "$STAMP" --validate >/dev/null && record PASS "assemble_validate" || record FAIL "assemble"

[[ -f "$PASTE" ]] && record PASS "paste_artifact" || record FAIL "paste_artifact"
"$DIR/validate-output.sh" newsletter-paste "$PASTE" >/dev/null && record PASS "paste_gate" || record FAIL "paste_gate"

grep -q 'mode: notion_paste' "$WORKDIR/config/newsletter.yaml" && record PASS "delivery_config" || record FAIL "delivery_config"
grep -q 'esp_send: false' "$WORKDIR/config/newsletter.yaml" && record PASS "no_esp_send" || record FAIL "no_esp"

"$DIR/archive-to-notion.sh" "$STAMP" --force >/dev/null 2>&1 && record PASS "notion_sync" || record FAIL "notion_sync"

python3 <<PY && record PASS "notion_paste_canonical" || record FAIL "notion_tier"
import json
from pathlib import Path
stamp = "${STAMP}"
state = json.loads((Path.home() / "hermes-content-studio/content/.notion-archive-state.json").read_text())
meta = state.get("pages", {}).get(f"{stamp}/newsletter_paste")
assert meta and meta.get("tier") == "canonical", meta
assert meta.get("url"), meta
print(meta["url"])
PY

PASTE_URL=$(python3 -c "import json; s=json.load(open('$WORKDIR/content/.notion-archive-state.json')); print(s['pages']['$STAMP/newsletter_paste']['url'])")

{
  echo "# Newsletter P6 Eval — $STAMP"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL**"
  echo ""
  echo "## P6 — Notion 붙여넣기 팩"
  echo "- ESP/API 발송 없음"
  echo "- Notion 코드 블록 → 외부 플랫폼 문서 편집기"
  echo ""
  echo "## Notion Permalink"
  echo "- Newsletter Paste: $PASTE_URL"
  echo ""
  echo "## 로컬 산출물"
  echo "- \`content/packages/${STAMP}_newsletter-paste.md\`"
} > "$REPORT"

echo "Report: $REPORT"
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
