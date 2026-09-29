#!/usr/bin/env bash
# Demand radar eval — 샘플 데이터 · 결정적 · 네트워크 없음
#
# 검사: 급상승 규칙 · 잡음 제외 · 누락 주차=0 · 제안 개수 상한 · Slack 문구 ·
#       API 요청 분할/헤더(모의) · M1 자동 병합 없음 · 샘플 Notion/cron 제외
# Usage: ./scripts/demand-radar-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Demand Radar Eval ==="
TMP_WS="$(mktemp -d)"
trap 'rm -rf "$TMP_WS"' EXIT

OUT=$(cd "$DIR" && HERMES_WORKDIR="$TMP_WS" PYTHONPATH="$DIR" python3 - <<'PY'
import copy
import json
import os
import urllib.request
from datetime import date
from lib import demand_radar as R

def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)

cfg = R.load_config()
cfg["mode"] = "sample"
r = R.build_radar(cfg)
rising = [k.keyword for k in r.rising]

# 1) rule
check("rising_set", set(rising) == {"GEO 최적화", "생성형 AI 교육", "AI 에이전트", "AI 검색 최적화"})
check("rising_sorted_by_growth", rising[0] == "GEO 최적화")
aeo = next(k for k in r.keywords if k.keyword == "AEO")
check("tiny_baseline_filtered", not aeo.rising and aeo.growth_pct and aeo.growth_pct > 100)
check("missing_weeks_are_zero", len(aeo.series) == 12 and aeo.series[0] == 0.0)
capped = copy.deepcopy(cfg); capped["rising"]["max_suggestions"] = 2
check("suggestion_cap", len(R.build_radar(capped).rising) == 2)

# 2) messages
msg = R.format_slack(r, cfg, "x.md")
check("slack_has_research_commands", "/research GEO 최적화" in msg and "자동" not in msg.split("\n")[0])
check("slack_has_source_and_caveat", "출처:" in msg and "상대값" in msg)
check("slack_marks_sample", msg.startswith("[샘플]"))
quiet = copy.deepcopy(cfg); quiet["rising"]["min_growth_pct"] = 999
check("no_rising_one_line", "\n" not in R.format_slack(R.build_radar(quiet), quiet, "x.md"))
check("sample_skips_notion", R.output_path(r, cfg).name.startswith("_sample_"))

# 3) periods
check("week_range", R.week_range(date(2026, 9, 29), 12) == ("2026-07-06", "2026-09-27"))

# 4) API: ≤5 groups per request, hub headers, no keys → error (mocked, no network)
calls = []
class FakeResp:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return json.dumps(self.body).encode()
def fake_urlopen(req, timeout=0):
    body = json.loads(req.data.decode())
    calls.append((req.get_method(), req.full_url, dict(req.header_items()), body))
    return FakeResp({"results": [{"title": g["groupName"], "keywords": g["keywords"], "data": []} for g in body["keywordGroups"]]})
api = copy.deepcopy(cfg); api["mode"] = "api"
api["themes"] = {"T": [f"k{i}" for i in range(7)]}
os.environ.update({"NAVER_HUB_API_KEY_ID": "id", "NAVER_HUB_API_KEY": "key"})
orig = urllib.request.urlopen
urllib.request.urlopen = fake_urlopen
try:
    R.build_radar(api, today=date(2026, 9, 29))
finally:
    urllib.request.urlopen = orig
group_sizes = [len(c[3]["keywordGroups"]) for c in calls]
check("api_batches_max_5_groups", group_sizes == [5, 2, 1])
check("api_hub_headers", all("X-ncp-apigw-api-key-id" in c[2] for c in calls))
check("api_weekly_window", calls[0][3]["startDate"] == "2026-07-06" and calls[0][3]["timeUnit"] == "week")
for k in ("NAVER_HUB_API_KEY_ID", "NAVER_HUB_API_KEY"):
    os.environ.pop(k)
os.environ["HERMES_ENV"] = "/nonexistent"
try:
    R.build_radar(api, today=date(2026, 9, 29)); check("api_requires_keys", False)
except R.DataLabError:
    check("api_requires_keys", True)
PY
)
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  record "${line%% *}" "${line#* }"
done <<< "$OUT"

# 5) Never merges into M1 on its own
if grep -nE 'HERMES_RESEARCH_KEYWORDS|run-keyword-research|research_staging|run-research-brief' \
    "$DIR/lib/demand_radar.py" "$DIR/demand-radar.py" "$DIR/cron-demand-radar.sh" >/dev/null; then
  record FAIL "no_auto_merge_into_m1"
else
  record PASS "no_auto_merge_into_m1"
fi

# 6) Sample mode never registers cron
if HERMES_DEMAND_RADAR_MODE=sample HERMES_WORKDIR="$REPO" bash "$DIR/setup-demand-radar-cron.sh" --dry-run 2>&1 | grep -q '등록하지 않습니다'; then
  record PASS "sample_mode_no_cron"
else
  record FAIL "sample_mode_no_cron"
fi

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
