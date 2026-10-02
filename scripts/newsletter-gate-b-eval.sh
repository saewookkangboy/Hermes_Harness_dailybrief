#!/usr/bin/env bash
# Gate B — 이메일 장문 · LinkedIn · CTA · 16:9 이미지 프롬프트
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAMP="${1:-$(date +%Y-%m-%d)}"
if [[ ! -f "$WORKDIR/content/research/${STAMP}_brief.md" ]]; then
  LATEST=$(ls -1 "$WORKDIR/content/research/"*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1)
  [[ -n "$LATEST" ]] && STAMP="$LATEST"
fi

echo "=== Newsletter Gate B — $STAMP ==="
export HERMES_ENHANCE=0
"$DIR/run-newsletter.sh" "$STAMP"

python3 - "$DIR" "$WORKDIR" "$STAMP" <<'PY'
import re
import sys
from pathlib import Path

DIR, WORKDIR, stamp = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, DIR)

from lib.newsletter_cta import cta_failures
from lib.newsletter_gates import assert_freshness
from lib.newsletter_linkedin import _word_count, linkedin_length_ok
from lib.newsletter_quality import load_newsletter_config

cfg = load_newsletter_config()
targets = cfg.get("length_targets") or {}
email_lo, email_hi = (targets.get("email_words") or [600, 1200])[:2]
li_lo, li_hi = (targets.get("linkedin_words") or [800, 1500])[:2]

img = WORKDIR / "content" / "newsletter" / f"{stamp}_title-image-16x9.md"
paste = WORKDIR / "content" / "packages" / f"{stamp}_newsletter-paste.md"
li = WORKDIR / "content" / "linkedin" / f"{stamp}_newsletter-article.md"
htmls = sorted(
    (WORKDIR / "content" / "newsletter").glob(f"{stamp}_newsletter_*.html"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
# Exclude title-image and non-body artifacts from newsletter md glob
nls = [
    p
    for p in sorted(
        (WORKDIR / "content" / "newsletter").glob(f"{stamp}_newsletter_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if "title-image" not in p.name and "subject-scores" not in p.name
]

pass_n = fail_n = 0

def check(name, ok, detail=""):
    global pass_n, fail_n
    if ok:
        print(f"PASS {name}" + (f" {detail}" if detail else ""))
        pass_n += 1
    else:
        print(f"FAIL {name}" + (f" {detail}" if detail else ""))
        fail_n += 1

check("newsletter_md", bool(nls))
check("paste_pack", paste.exists())
check("linkedin_article", li.exists())
check("title_image_prompt", img.exists())
check("html_email", bool(htmls))

if nls:
    text = nls[0].read_text(encoding="utf-8")
    # count reader body only
    body = text
    if "## 타이틀 이미지" in body:
        body = body.split("## 타이틀 이미지", 1)[1]
    if "## 품질 메모" in body:
        body = body.split("## 품질 메모", 1)[0]
    wc = _word_count(body)
    check("email_length", email_lo <= wc <= email_hi + 250, f"words={wc} target={email_lo}-{email_hi}")
    check("email_structure", all(x in text for x in ("## 30초 TLDR", "## 오늘의 1가지", "### 1.", "## 이번 주 실습", "TITLE_IMAGE_16x9")))
    fails = assert_freshness(stamp, text, cfg) + cta_failures(text)
    check("email_gates", not fails, str(fails) if fails else "")
    # CTA https present
    check("cta_https", "https://" in text.split("## 이번 주 실습", 1)[-1].split("## 다음 호", 1)[0])

if li.exists():
    lit = li.read_text(encoding="utf-8")
    lwc = _word_count(lit)
    check("linkedin_length", linkedin_length_ok(lit, lo=li_lo, hi=li_hi), f"words={lwc} target={li_lo}-{li_hi}")
    h2 = len(re.findall(r"^## ", lit, re.M))
    check("linkedin_sections", h2 >= 4, f"h2={h2}")
    check("linkedin_image_slot", "타이틀 이미지" in lit or "16:9" in lit)

if img.exists():
    it = img.read_text(encoding="utf-8")
    check("image_prompt_16x9", "16:9" in it and "```" in it and "Alt text" in it)

if paste.exists():
    pt = paste.read_text(encoding="utf-8")
    check("paste_sections", all(f"## §{i}" in pt for i in range(1, 8)))

if htmls:
    ht = htmls[0].read_text(encoding="utf-8")
    check("html_image_slot", "TITLE_IMAGE_16x9" in ht)
    check("html_no_hash_cta", "href='#'" not in ht and 'href="#"' not in ht)

print(f"=== Gate B Result PASS={pass_n} FAIL={fail_n} ===")
raise SystemExit(0 if fail_n == 0 else 1)
PY
