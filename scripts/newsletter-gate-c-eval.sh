#!/usr/bin/env bash
# Gate C — validate + publish blocking + fail-injection
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

echo "=== Newsletter Gate C — $STAMP ==="
export HERMES_ENHANCE=0

# Good path
if ! "$DIR/run-newsletter.sh" "$STAMP" --validate; then
  echo "FAIL good_path_validate"
  exit 1
fi
echo "PASS good_path_validate"

python3 - "$DIR" "$WORKDIR" "$STAMP" <<'PY'
import json
import sys
from pathlib import Path

DIR, WORKDIR, stamp = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, DIR)

from lib.newsletter_gates import evaluate_publishability, is_publishable, write_publish_status

pass_n = fail_n = 0

def check(name, ok, detail=""):
    global pass_n, fail_n
    if ok:
        print(f"PASS {name}" + (f" {detail}" if detail else ""))
        pass_n += 1
    else:
        print(f"FAIL {name}" + (f" {detail}" if detail else ""))
        fail_n += 1

pub = WORKDIR / "content" / "packages" / f"{stamp}_newsletter-publish.json"
check("publish_json", pub.exists())
data = json.loads(pub.read_text(encoding="utf-8")) if pub.exists() else {}
check("publishable_true", bool(data.get("publishable")), str(data.get("failures")))

nls = [
    p
    for p in (WORKDIR / "content" / "newsletter").glob(f"{stamp}_newsletter_*.md")
    if "title-image" not in p.name
]
nl = sorted(nls, key=lambda p: p.stat().st_mtime, reverse=True)[0]
text = nl.read_text(encoding="utf-8")
check("no_dup_silmu", "실무 실무" not in text)
check("no_meta_insight", "번째 인사이트" not in text)
check("no_direct_answer_boilerplate", "블로그 Direct Answer + SEO/AEO/GEO 통합" not in text)
# hero density: unique + near-dup (Jaccard)
import re
from lib.newsletter_prose import sentence_similar

hero_m = re.search(r"## 오늘의 1가지\n\n(.+?)\n\n---", text, re.S)
hero = hero_m.group(1) if hero_m else ""
sents = [s.strip() for s in re.split(r"(?<=[.!?。])\s+", hero) if s.strip()]
norms = [re.sub(r"\s+", "", s.lower())[:36] for s in sents]
near = any(
    sentence_similar(a, b, threshold=0.72)
    for i, a in enumerate(sents)
    for b in sents[i + 1 :]
)
check(
    "hero_unique_sentences",
    len(norms) == len(set(norms)) and len(sents) >= 3 and not near,
    f"n={len(sents)} near={near}",
)
check("no_generic_insight_boilerplate", "2026 AI·마케팅 실무 인사이트" not in text)
check("no_reinterpret_boilerplate", "브랜드·퍼포먼스·콘텐츠·AX 관점에서 재해석" not in text)

# Fail-injection: corrupt CTA then evaluate should be not publishable
backup = text
corrupted = text.replace("https://", "http://BROKEN/", 1)
# stronger: inject placeholder
if "## 이번 주 실습 1가지" in corrupted:
    pre, rest = corrupted.split("## 이번 주 실습 1가지", 1)
    rest = rest.split("## 다음 호", 1)
    mid = "\n\n링크는 여기 1곳만: 통합 컨텍스트에서 전문을 확인하세요.\n\n"
    corrupted = pre + "## 이번 주 실습 1가지" + mid + "## 다음 호" + (rest[1] if len(rest) > 1 else "")
nl.write_text(corrupted, encoding="utf-8")
write_publish_status(stamp)
bad = json.loads(pub.read_text(encoding="utf-8"))
check("fail_injection_blocks", bad.get("publishable") is False, str(bad.get("failures")))
# restore
nl.write_text(backup, encoding="utf-8")
write_publish_status(stamp)
check("restored_publishable", is_publishable(stamp))

# Notion skip: when not publishable, newsletter cats should be filtered
nl.write_text(corrupted, encoding="utf-8")
write_publish_status(stamp)
sys.path.insert(0, str(WORKDIR / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("archive_to_notion", WORKDIR / "scripts" / "archive-to-notion.py")
mod = importlib.util.module_from_spec(spec)
# Avoid running main — only load helpers if import side effects are heavy; test is_publishable path instead
check("notion_block_flag", not is_publishable(stamp))
nl.write_text(backup, encoding="utf-8")
write_publish_status(stamp)

print(f"=== Gate C Result PASS={pass_n} FAIL={fail_n} ===")
raise SystemExit(0 if fail_n == 0 else 1)
PY
