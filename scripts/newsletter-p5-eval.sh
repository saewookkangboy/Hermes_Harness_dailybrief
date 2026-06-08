#!/usr/bin/env bash
# P5 — ESP dry-run manifest · HITL 발송 경로
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

REPORT="$WORKDIR/content/logs/${STAMP}_newsletter-p5-eval-report.md"
mkdir -p "$WORKDIR/content/logs"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Newsletter P5 Eval — $STAMP ==="

"$DIR/newsletter-p4-eval.sh" "$STAMP" >/dev/null 2>&1 && record PASS "p4_regression" || record FAIL "p4_regression"

"$DIR/newsletter-send.sh" "$STAMP" >/dev/null && record PASS "esp_dry_run" || record FAIL "esp_dry_run"

MANIFEST="$WORKDIR/content/logs/${STAMP}_newsletter-send-manifest.json"
[[ -f "$MANIFEST" ]] && record PASS "manifest_artifact" || record FAIL "manifest"

python3 <<PY && record PASS "manifest_fields" || record FAIL "manifest_fields"
import json
from pathlib import Path
m = json.loads(Path("${MANIFEST}").read_text())
for k in ("subject", "html_path", "preheader", "mode"):
    assert m.get(k), k
assert m["mode"] == "dry_run"
assert Path(m["html_path"]).exists()
PY

grep -q "esp:" "$WORKDIR/config/newsletter.yaml" && record PASS "esp_config" || record FAIL "esp_config"

{
  echo "# Newsletter P5 Eval — $STAMP"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL**"
  echo ""
  echo "## P5 범위"
  echo "- ESP dry-run manifest (newsletter-send.sh)"
  echo "- config/newsletter.yaml esp 블록"
  echo ""
  echo "## Manifest"
  echo "- \`content/logs/${STAMP}_newsletter-send-manifest.json\`"
} > "$REPORT"

echo "Report: $REPORT"
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
