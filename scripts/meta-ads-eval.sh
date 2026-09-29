#!/usr/bin/env bash
# Meta Ads loop eval — 샘플 데이터 · 결정적 · 네트워크 없음
#
# 검사: 피로도 판정 규칙 · 0건 무게시 · 출처 표기 · 조회 전용 보장 ·
#       API 페이지네이션 파싱(모의 응답) · 샘플의 Notion/Git 제외
# Usage: ./scripts/meta-ads-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Meta Ads Eval ==="
TMP_WS="$(mktemp -d)"
trap 'rm -rf "$TMP_WS"' EXIT

OUT=$(cd "$DIR" && HERMES_WORKDIR="$TMP_WS" PYTHONPATH="$DIR" python3 - <<'PY'
import json
import urllib.request
from lib import meta_ads as M

def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)

cfg = M.load_config()
cfg["mode"] = "sample"
ins = M.load_insights(cfg)
rows = M.evaluate_fatigue(ins, cfg)
flagged = {r.cur.adset_name for r in rows if r.fatigued}

# 1) rule: all three conditions, nothing else
check("flags_retargeting_and_webinar", flagged == {"AX교육_리타게팅_30일", "웨비나_유사타깃_1%"})
check("low_impressions_not_flagged", "가이드북_다운로드_관심사" not in flagged)
check("stable_ctr_not_flagged", "뉴스레터_구독_리드폼" not in flagged)
check("low_frequency_not_flagged", "브랜드_인지도_동영상" not in flagged)

# 2) alert text: source/period/conditions + no-change statement; empty when nothing flagged
alert = M.format_fatigue_alert(ins, rows, cfg)
check("alert_has_source_period_conditions", all(s in alert for s in ("출처:", "2026-09-22~2026-09-28", "빈도≥3.5")))
check("alert_says_no_account_change", "바꾸지 않았습니다" in alert)
strict = {**cfg, "fatigue": {**cfg["fatigue"], "max_frequency": 99}}
check("no_flag_no_post", M.format_fatigue_alert(ins, M.evaluate_fatigue(ins, strict), strict) == "")

# 3) weekly report numbers are consistent with the fixture
report = M.format_weekly_report(ins, rows, cfg)
t = M.totals(ins.current)
check("weekly_totals", round(t["spend"]) == 2212000 and round(t["conversions"]) == 105)
check("weekly_marks_sample", "샘플 데이터" in report)
check("sample_outputs_skip_notion", M.output_path("weekly", ins, cfg).name.startswith("_sample_"))

# 4) API path: paging + GET only (mocked, no network)
pages = [
    {"data": [{"adset_id": "1", "adset_name": "A", "campaign_name": "C", "impressions": "6000", "reach": "1500",
               "clicks": "30", "spend": "1000", "actions": [{"action_type": "lead", "value": "2"}]}],
     "paging": {"next": "https://graph.facebook.com/next-page"}},
    {"data": [{"adset_id": "2", "adset_name": "B", "campaign_name": "C", "impressions": "100", "reach": "90",
               "clicks": "1", "spend": "10"}]},
]
seen = []
class FakeResp:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return json.dumps(self.body).encode()
def fake_urlopen(req, timeout=0):
    seen.append((req.get_method(), req.full_url))
    return FakeResp(pages[len(seen) - 1])
orig = urllib.request.urlopen
urllib.request.urlopen = fake_urlopen
try:
    got = M._fetch_window(cfg, "TOKEN", "123", "2026-09-22", "2026-09-28")
finally:
    urllib.request.urlopen = orig
stats = [M.AdSetStats.from_row(r, cfg["conversion_action_types"]) for r in got]
check("api_follows_paging", len(got) == 2 and len(seen) == 2)
check("api_get_only", all(m == "GET" for m, _ in seen))
check("api_derives_frequency_ctr", abs(stats[0].frequency - 4.0) < 1e-9 and abs(stats[0].ctr - 0.5) < 1e-9 and stats[0].conversions == 2)
check("api_uses_insights_endpoint", "/act_123/insights?" in seen[0][1] and "level=adset" in seen[0][1])
PY
)
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  record "${line%% *}" "${line#* }"
done <<< "$OUT"

# 5) Read-only by construction: no write verbs anywhere in the loop code
if grep -nE 'method="(POST|DELETE|PUT)"|"POST"|urlopen\([^)]*data=' "$DIR/lib/meta_ads.py" "$DIR/meta-ads.py" >/dev/null; then
  record FAIL "loop_code_has_no_write_calls"
else
  record PASS "loop_code_has_no_write_calls"
fi

# 6) Ad performance never lands in git (public repo)
git -C "$REPO" check-ignore -q content/ads/2026-01-01_meta-weekly-report.md \
  && record PASS "content_ads_gitignored" || record FAIL "content_ads_gitignored"

# 7) Sample mode never registers cron
if HERMES_META_ADS_MODE=sample HERMES_WORKDIR="$REPO" bash "$DIR/setup-meta-ads-cron.sh" --dry-run 2>&1 | grep -q '등록하지 않습니다'; then
  record PASS "sample_mode_no_cron"
else
  record FAIL "sample_mode_no_cron"
fi

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
