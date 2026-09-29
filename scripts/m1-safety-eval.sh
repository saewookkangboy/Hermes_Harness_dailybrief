#!/usr/bin/env bash
# M1 safety & classification regression eval — 결정적, LLM 0회
#
# 2026-09-29 감사에서 확인된 회귀를 고정합니다:
#   - NSFW·광고 클릭 URL이 M1 필터를 통과해 브리프·wiki에 들어감
#   - 검색어의 'Korea'만으로 글로벌 기사가 '대한민국' 분류가 됨
#   - build-graph / wiki seed가 옛 브리프의 차단 출처를 다시 끌어옴
#
# Usage: ./scripts/m1-safety-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== M1 Safety Eval ==="

OUT=$(cd "$DIR" && PYTHONPATH="$DIR" python3 - <<'PY'
import importlib.util
import sys
from pathlib import Path

from lib.brief_quality import classify_insight, has_korea_evidence, is_usable_search_result
from lib.content_safety import is_unsafe

def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)

korea_q = "Korea AX AI transformation news 2026"
adopt_q = "Korea enterprise AI agent adoption 2026"

def item(title, url, snippet="", query=korea_q):
    return {"title": title, "url": url, "snippet": snippet, "query": query}

# 1) Unsafe sources never pass M1 intake
check("m1_blocks_undress", not is_usable_search_result(item("UndressHer AI – Best Undress AI Tools 2026 | Free Demo & Reviews", "https://undress-her.com/", "Try the best AI tools free")))
check("m1_blocks_nudify", not is_usable_search_result(item("Free AI Nudify App 2026 - No Signup", "https://example-nudify.app/", "AI photo tool")))
check("m1_blocks_ad_click", not is_usable_search_result(item("ChatGPT AI powered AI Chatbot - Use AI", "https://www.bing.com/aclick?ld=abc", "Use AI now")))
check("m1_keeps_normal_news", is_usable_search_result(item("KT unveils 18 tn won AX transformation plan", "https://pulse.mk.co.kr/news/english/12092359", "KT announced an AI transformation plan for Korea")))

# 2) The search query is not evidence of Korea
check("global_stat_not_korea", not classify_insight("AI Adoption Gap: 80% of Orgs See Value, 39% Struggle", "Enterprise AI agent adoption in 2026 shows a widening gap", adopt_q).startswith("korea"))
check("europe_event_not_korea", not classify_insight("Enterprise AI Marketing Transformation Assembly Europe – June 2025", "Join marketing leaders in London", korea_q).startswith("korea"))
check("korean_news_still_korea", classify_insight("KT unveils 18 tn won AX transformation plan", "KT announced an AI transformation plan", korea_q).startswith("korea"))
check("korean_domestic_title_korea", classify_insight("'2026 한경 AX 서밋' 첫 개최…국내 기업 우수사례 한자리에", "", korea_q).startswith("korea"))
check("korean_language_foreign_not_korea", not classify_insight("프랑스 미스트랄, 새 오픈소스 AI 모델 공개", "유럽 AI 스타트업의 신규 모델", korea_q).startswith("korea"))
# "Korean" / "한국어" name the language, not the country
check("korean_translation_not_korea_evidence", not has_korea_evidence("Korean translation of the French AI announcement"))
check("korean_translation_not_korea_class", not classify_insight("Korean translation of the French AI transformation announcement", "", "AI news 2026").startswith("korea"))
check("hangul_korean_language_not_korea", not has_korea_evidence("미스트랄 발표문 한국어 번역본 공개"))
check("korea_name_still_evidence", all(has_korea_evidence(t) for t in ("South Korea's AI push", "Korea가 AI 투자 확대", "한국 기업 AX 사례")))

# 3) Graph + wiki never re-ingest blocked sources from historical briefs
spec = importlib.util.spec_from_file_location("build_graph", Path("build-graph.py"))
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)
pairs = bg.extract_source_claims(
    "한국 AX 전환 신호입니다. 국내 기업 68% 가 도입 중입니다.\n- **출처:** https://undress-her.com/\n\n"
    "KT는 18조 원 규모 AX 계획을 발표했습니다.\n- **출처:** https://pulse.mk.co.kr/news/english/12092359"
)
urls = {u for u, _ in pairs}
check("graph_skips_unsafe_url", "https://undress-her.com/" not in urls and any("mk.co.kr" in u for u in urls))
check("safety_list_shared_with_newsletter", is_unsafe("https://x.example/nudify-tool"))
pairs = bg.extract_source_claims(
    "국내 기업 68% 가 AX 도입을 검토 중이라고 밝혔습니다.\n"
    "https://undress-her.com/a https://nudify.example/b https://www.bing.com/aclick?x=1 https://pulse.mk.co.kr/news/1"
)
check("graph_caps_after_filtering", any("mk.co.kr" in u for u, _ in pairs))

# 4) Wiki seed: a blocked latest node supplies neither heading nor summary
import tempfile
import lib.wiki_seed as WS
WS.CONCEPTS_DIR = Path(tempfile.mkdtemp())
out = WS._write_concept("korea_ax", [
    {"title": "UndressHer AI – Best Undress AI Tools", "url": "https://undress-her.com/", "stamp": "2026-09-14"},
    {"title": "KT unveils 18 tn won AX plan", "url": "https://pulse.mk.co.kr/news/1", "stamp": "2026-09-13"},
], 1)
text = out.read_text(encoding="utf-8") if out else ""
check("wiki_seed_blocked_latest_not_in_page", "Undress" not in text and "KT unveils" in text)
check("wiki_seed_all_blocked_skips_page", WS._write_concept("x", [{"title": "Nudify", "url": "https://nudify.example/"}], 0) is None)

# 4b) Full seed: blocked nodes stay out of the index and cross-links; a page whose
#     sources are now all blocked is removed rather than left from an earlier run
root = Path(tempfile.mkdtemp())
WS.WIKI_ROOT, WS.CONCEPTS_DIR = root, root / "concepts"
WS.INDEX_PATH, WS.LOG_PATH = root / "index.md", root / "log.md"
WS.CONCEPTS_DIR.mkdir(parents=True)
(WS.CONCEPTS_DIR / "blocked_only.md").write_text("# Nudify old page\n", encoding="utf-8")
WS.load_brief_graph = lambda: {"nodes": [
    {"topic_key": "korea_ax", "title": "UndressHer AI – Best Undress AI Tools", "url": "https://undress-her.com/", "stamp": "2026-09-14"},
    {"topic_key": "korea_ax", "title": "KT unveils 18 tn won AX plan", "url": "https://pulse.mk.co.kr/news/1", "stamp": "2026-09-13"},
    {"topic_key": "blocked_only", "title": "Free Nudify App", "url": "https://nudify.example/", "stamp": "2026-09-14"},
    {"topic_key": "ai_ide", "title": "Cursor ships background agents", "url": "https://cursor.com/blog/x", "stamp": "2026-09-12"},
], "streaks": []}
res = WS.seed_from_brief_graph()
index = WS.INDEX_PATH.read_text(encoding="utf-8")
korea_page = (WS.CONCEPTS_DIR / "korea_ax.md").read_text(encoding="utf-8")
check("wiki_index_skips_blocked_latest", "Undress" not in index and "KT unveils" in index)
check("wiki_index_skips_blocked_topic", "blocked_only" not in index and "Nudify" not in index)
check("wiki_links_only_written_pages", "[[blocked_only]]" not in korea_page and "[[ai_ide]]" in korea_page)
check("wiki_removes_now_blocked_page", not (WS.CONCEPTS_DIR / "blocked_only.md").exists() and res.get("concepts") == 2)

# 5) Newsletter gate follows config/newsletter.yaml, not only its own regex
import lib.content_safety as CS
from lib.newsletter_gates import assert_freshness
orig = CS._lists
CS._lists = lambda: (("forbidden-term-x",), ())
try:
    fails = assert_freshness("2099-01-01", "**권장 제목:** `테스트`\n\n본문 forbidden-term-x 포함", {})
finally:
    CS._lists = orig
check("newsletter_gate_uses_shared_policy", "unsafe_content" in fails)
PY
)
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  record "${line%% *}" "${line#* }"
done <<< "$OUT"

# 6) Wiki no longer cites blocked sources
if grep -rqiE 'undress|nudify|deepnude' "$REPO/content/wiki" 2>/dev/null; then
  record FAIL "wiki_clean_of_blocked_sources"
else
  record PASS "wiki_clean_of_blocked_sources"
fi

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
