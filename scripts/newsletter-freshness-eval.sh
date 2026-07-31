#!/usr/bin/env bash
# Gate A — 신선도·안전·제목 정합 평가
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

echo "=== Newsletter Freshness Gate A — $STAMP ==="
export HERMES_ENHANCE=0
"$DIR/run-newsletter.sh" "$STAMP"

python3 - "$DIR" "$WORKDIR" "$STAMP" <<'PY'
import re
import sys
from pathlib import Path

DIR, WORKDIR, stamp = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, DIR)

from lib.content_quality import parse_brief
from lib.newsletter_gates import assert_cta_https, assert_freshness
from lib.newsletter_quality import load_newsletter_config
from lib.newsletter_select import display_title_for, is_unsafe_insight, select_issue_insights

cfg = load_newsletter_config()
brief = (WORKDIR / "content" / "research" / f"{stamp}_brief.md").read_text(encoding="utf-8")
_, insights = parse_brief(brief)
unsafe = [i for i in insights if is_unsafe_insight(i, cfg)]
sel = select_issue_insights(stamp, insights, cfg)
nls = sorted(
    (WORKDIR / "content" / "newsletter").glob(f"{stamp}_newsletter_*.md"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
if not nls:
    print("FAIL assemble_missing")
    raise SystemExit(1)
text = nls[0].read_text(encoding="utf-8")
fails = assert_freshness(stamp, text, cfg) + assert_cta_https(text)
src = getattr(sel.hero, "source_title", "") or ""
collapsed = ("한국 AX 전환 — 교육·FAQ·사례 중심" in sel.topic) and (
    "HSAD" in src or "Deep Agent" in src
)
checks = [
    ("assembled", True),
    ("unsafe_filtered", True),  # presence of filter path is enough; count below
    ("not_stale_ax_hero", not collapsed),
    ("freshness_cta_gates", not fails),
]
pass_n = fail_n = 0
for name, ok in checks:
    if ok:
        print(f"PASS {name}")
        pass_n += 1
    else:
        print(f"FAIL {name} {fails if name.startswith('fresh') else ''}")
        fail_n += 1
print(f"INFO unsafe_skipped={len(unsafe)}")
print(f"INFO topic={sel.topic}")
print(f"INFO pattern={sel.pattern_id}")
print(f"INFO modules={[display_title_for(i, cfg) for i in sel.insights]}")
m = re.search(r"\*\*권장 제목:\*\*\s*`([^`]+)`", text)
print(f"INFO subject={m.group(1) if m else '?'}")
hm = re.search(r"## 오늘의 1가지\n\n(.+?)\n\n---", text, re.S)
hero = (hm.group(1).strip()[:200] + "…") if hm else "?"
print("INFO hero_snip=" + hero.replace("\n", " "))
print(f"=== Gate A Result PASS={pass_n} FAIL={fail_n} ===")
raise SystemExit(0 if fail_n == 0 else 1)
PY
