#!/usr/bin/env bash
# Research trust eval — URL · 중복 · 다양성 · 채널 훅 커버리지
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
BRIEF="$WORKDIR/content/research/${STAMP}_brief.md"
if [[ ! -f "$BRIEF" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1 || true)
  [[ -n "${LATEST:-}" ]] && STAMP="$LATEST" && BRIEF="$WORKDIR/content/research/${STAMP}_brief.md"
fi

REPORT="$WORKDIR/content/logs/${STAMP}_research-trust-eval-report.md"
mkdir -p "$WORKDIR/content/logs"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Research Trust Eval — $STAMP ==="
[[ -f "$BRIEF" ]] && record PASS "brief_exists" || record FAIL "brief_exists"

if [[ -f "$BRIEF" ]]; then
  "$DIR/validate-output.sh" research "$BRIEF" >/dev/null 2>&1 && record PASS "validate_research" || record FAIL "validate_research"

  EVAL_OUT=$(python3 - <<PY
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, "$DIR")
from lib.brief_quality import canonicalize_url, title_token_overlap

text = Path("$BRIEF").read_text(encoding="utf-8")
blocks = re.split(r"^### \d+\.\s+", text, flags=re.M)[1:]
urls = []
hooks = []
trusts = []
titles = []
for b in blocks:
    title = b.split("\n", 1)[0].strip()
    titles.append(title)
    m = re.search(r"- \*\*출처:\*\* (\S+)", b)
    urls.append(m.group(1) if m else "")
    h = re.search(r"- \*\*채널 훅:\*\* (.+)", b)
    hooks.append(h.group(1) if h else "")
    t = re.search(r"- \*\*신뢰도:\*\* (\w+)", b)
    trusts.append(t.group(1) if t else "")

n = len(blocks)
canon = [canonicalize_url(u) for u in urls if u]
dup_urls = n - len(set(canon)) if canon else n
near = 0
for i in range(len(titles)):
    for j in range(i + 1, len(titles)):
        if title_token_overlap(titles[i], titles[j]) >= 0.55:
            near += 1
https_ok = sum(1 for u in urls if u.startswith("http"))
hook_ok = sum(1 for h in hooks if all(k in h for k in ("blog=", "linkedin=", "instagram=", "newsletter=")))
trust_ok = sum(1 for t in trusts if t in ("high", "medium", "low"))

checks = [
    ("min_insights", n >= 7),
    ("https_coverage", https_ok == n and n > 0),
    ("dup_url_zero", dup_urls == 0),
    ("near_dup_zero", near == 0),
    ("hooks_coverage", hook_ok == n and n > 0),
    ("trust_coverage", trust_ok == n and n > 0),
]
for name, ok in checks:
    print(("PASS" if ok else "FAIL") + " " + name)
print(f"META insights={n} https={https_ok} dup_urls={dup_urls} near={near} hooks={hook_ok} trust={trust_ok}")
PY
)
  while IFS= read -r line; do
    [[ "$line" == META* ]] && echo "$line" && continue
    [[ "$line" == PASS* || "$line" == FAIL* ]] || continue
    record ${line%% *} "${line#* }"
  done <<< "$EVAL_OUT"
fi

{
  echo "# Research Trust Eval — $STAMP"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL**"
  echo ""
  echo "- Brief: \`$BRIEF\`"
} > "$REPORT"

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
echo "📄 $REPORT"
[[ "$FAIL" -eq 0 ]]
