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

from lib.brief_quality import classify_insight, is_usable_search_result
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
check("korean_language_title_korea", classify_insight("'2026 한경 AX 서밋' 첫 개최…최신트렌드·우수사례 한자리에", "", korea_q).startswith("korea"))

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
PY
)
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  record "${line%% *}" "${line#* }"
done <<< "$OUT"

# 4) Wiki no longer cites blocked sources
if grep -rqiE 'undress|nudify|deepnude' "$REPO/content/wiki" 2>/dev/null; then
  record FAIL "wiki_clean_of_blocked_sources"
else
  record PASS "wiki_clean_of_blocked_sources"
fi

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
