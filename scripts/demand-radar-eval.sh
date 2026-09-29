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

# 5b) A broken config fails loudly instead of falling back to sample mode
BROKEN=$(cd "$DIR" && PYTHONPATH="$DIR" python3 - <<'PY'
import tempfile
from pathlib import Path
from lib import demand_radar as R
bad = Path(tempfile.mkdtemp()) / "demand-radar.yaml"
bad.write_text("demand_radar:\n  mode: api\n  themes: [unclosed\n", encoding="utf-8")
R.CONFIG_PATH = bad
try:
    R.load_config(); print("FAIL")
except Exception:
    print("PASS")
PY
)
record "$BROKEN" "broken_config_fails_loudly"

# 5b2) Missing file or missing demand_radar section also stops (no silent sample mode)
MISSING=$(cd "$DIR" && PYTHONPATH="$DIR" python3 - <<'PY'
import tempfile
from pathlib import Path
from lib import demand_radar as R
d = Path(tempfile.mkdtemp())
ok = True
for path, text in ((d / "absent.yaml", None), (d / "nosection.yaml", "other: {}\n")):
    if text is not None:
        path.write_text(text, encoding="utf-8")
    R.CONFIG_PATH = path
    try:
        R.load_config(); ok = False
    except R.ConfigError:
        pass
print("PASS" if ok else "FAIL")
PY
)
record "$MISSING" "missing_config_fails_loudly"

# 5b2b) A misspelled mode stops too — setup would otherwise take the non-api branch and remove the job
INVALID=$(cd "$DIR" && PYTHONPATH="$DIR" python3 - <<'PY'
import os, tempfile
from pathlib import Path
from lib import demand_radar as R
d = Path(tempfile.mkdtemp())
os.environ.pop("HERMES_DEMAND_RADAR_MODE", None)
def mode_of(text, env=None):
    path = d / "c.yaml"; path.write_text(text, encoding="utf-8"); R.CONFIG_PATH = path
    if env: os.environ["HERMES_DEMAND_RADAR_MODE"] = env
    try:
        return R.load_config()["mode"]
    except R.ConfigError:
        return "ConfigError"
    finally:
        os.environ.pop("HERMES_DEMAND_RADAR_MODE", None)
ok = (mode_of("demand_radar:\n  mode: ap\n") == "ConfigError"
      and mode_of("demand_radar:\n  mode: api\n", env="bogus") == "ConfigError"
      and mode_of("demand_radar:\n  themes: {}\n") == "sample"
      and mode_of("demand_radar:\n  mode: api\n") == "api")
print("PASS" if ok else "FAIL")
PY
)
record "$INVALID" "invalid_mode_fails_loudly"

# 5b3) setup aborts on a config error — it must not reach the non-api branch that removes jobs
SBX="$(mktemp -d)"
mkdir -p "$SBX/scripts/lib" "$SBX/config" "$SBX/bin"
cp "$DIR/setup-demand-radar-cron.sh" "$SBX/scripts/"
cp "$DIR/lib/demand_radar.py" "$DIR/lib/slack_home.sh" "$SBX/scripts/lib/"
touch "$SBX/scripts/lib/__init__.py"
printf 'demand_radar:\n  mode: api\n  themes: [unclosed\n' > "$SBX/config/demand-radar.yaml"
printf '#!/usr/bin/env bash\n[[ "$1 $2" == "cron list" ]] && printf "  ab12cd34 [active]\\n    Name: cron-demand-radar\\n" || echo "$*" >> "%s/calls.log"\n' "$SBX" > "$SBX/bin/hermes"
chmod +x "$SBX/bin/hermes"
for case in broken invalid missing; do
  case "$case" in
    broken)  printf 'demand_radar:\n  mode: api\n  themes: [unclosed\n' > "$SBX/config/demand-radar.yaml" ;;
    invalid) printf 'demand_radar:\n  mode: ap\n' > "$SBX/config/demand-radar.yaml" ;;
    missing) rm -f "$SBX/config/demand-radar.yaml" ;;
  esac
  rm -f "$SBX/calls.log"
  if ! PATH="$SBX/bin:$PATH" HERMES_WORKDIR="$SBX" bash "$SBX/scripts/setup-demand-radar-cron.sh" >/dev/null 2>&1 && [[ ! -s "$SBX/calls.log" ]]; then
    record PASS "setup_aborts_on_${case}_config"
  else
    record FAIL "setup_aborts_on_${case}_config ($(cat "$SBX/calls.log" 2>/dev/null))"
  fi
done
rm -rf "$SBX"

# 5b4) The setup probe queries only — no report file that Notion could archive
PROBE_WS="$(mktemp -d)"
if HERMES_WORKDIR="$PROBE_WS" python3 "$DIR/demand-radar.py" --mode sample --probe | grep -q 'probe ok' \
   && [[ -z "$(find "$PROBE_WS" -name '*demand-radar.md' 2>/dev/null)" ]] \
   && grep -q -- '--probe' "$DIR/setup-demand-radar-cron.sh"; then
  record PASS "probe_writes_no_report"
else
  record FAIL "probe_writes_no_report"
fi
rm -rf "$PROBE_WS"

# 5c) Cron wrapper posts nothing outside api mode
grep -q -- '--require-api' "$DIR/cron-demand-radar.sh" \
  && [[ -z "$(HERMES_DEMAND_RADAR_MODE=sample HERMES_WORKDIR="$TMP_WS" python3 "$DIR/demand-radar.py" --require-api 2>/dev/null)" ]] \
  && record PASS "cron_sample_mode_posts_nothing" || record FAIL "cron_sample_mode_posts_nothing"

# 5d) Switching back to sample mode removes a job registered earlier in api mode
STUB="$(mktemp -d)"
cat > "$STUB/hermes" <<'SH'
#!/usr/bin/env bash
if [[ "$1 $2" == "cron list" ]]; then
  printf '  ab12cd34 [active]\n    Name:      cron-demand-radar\n  ef56ab78 [active]\n    Name:      cron-meta-weekly\n  99aa88bb [active]\n    Name:      cron-demand-radar-old\n'
else
  echo "$*" >> "$(dirname "$0")/calls.log"
fi
SH
chmod +x "$STUB/hermes"
PATH="$STUB:$PATH" HERMES_DEMAND_RADAR_MODE=sample HERMES_WORKDIR="$REPO" bash "$DIR/setup-demand-radar-cron.sh" >/dev/null 2>&1 || true
grep -q "cron remove ab12cd34" "$STUB/calls.log" 2>/dev/null \
  && record PASS "sample_mode_removes_existing_job" || record FAIL "sample_mode_removes_existing_job"
grep -q 99aa88bb "$STUB/calls.log" 2>/dev/null \
  && record FAIL "setup_removes_only_exact_name" || record PASS "setup_removes_only_exact_name"
rm -rf "$STUB"

# 5e) api mode: a failed lookup or removal stops setup before it registers a duplicate job
SBX="$(mktemp -d)"
mkdir -p "$SBX/scripts/lib" "$SBX/config" "$SBX/bin" "$SBX/home"
cp "$DIR/setup-demand-radar-cron.sh" "$DIR/cron-demand-radar.sh" "$SBX/scripts/"
cp "$DIR/lib/demand_radar.py" "$DIR/lib/slack_home.sh" "$DIR/lib/cron_bootstrap.sh" "$SBX/scripts/lib/"
touch "$SBX/scripts/lib/__init__.py"
cp "$REPO/config/demand-radar.yaml" "$SBX/config/"
printf 'import sys\nsys.exit(0)\n' > "$SBX/scripts/demand-radar.py"   # probe stub (no network)
cat > "$SBX/bin/hermes" <<'SH'
#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
case "$1 $2" in
  "cron list")
    [[ "${STUB_FAIL:-}" == list ]] && exit 1
    printf '  ab12cd34 [active]\n    Name:      cron-demand-radar\n  99aa88bb [active]\n    Name:      cron-demand-radar-old\n' ;;
  "cron remove") [[ "${STUB_FAIL:-}" == remove ]] && exit 1 ;;
esac
exit 0
SH
chmod +x "$SBX/bin/hermes"
api_setup() {
  rm -f "$SBX/calls.log"
  PATH="$SBX/bin:$PATH" HOME="$SBX/home" HERMES_WORKDIR="$SBX" HERMES_DEMAND_RADAR_MODE=api DEMAND_RADAR_DELIVER=telegram \
    STUB_LOG="$SBX/calls.log" STUB_FAIL="$1" bash "$SBX/scripts/setup-demand-radar-cron.sh" >/dev/null 2>&1
}
for fail in list remove; do
  if ! api_setup "$fail" && ! grep -q "cron create" "$SBX/calls.log" 2>/dev/null; then
    record PASS "setup_stops_when_cron_${fail}_fails"
  else
    record FAIL "setup_stops_when_cron_${fail}_fails ($(grep -c 'cron create' "$SBX/calls.log" 2>/dev/null) creates)"
  fi
done
if api_setup "" && [[ "$(grep -c 'cron create' "$SBX/calls.log")" == 1 ]] \
   && grep -q "cron remove ab12cd34" "$SBX/calls.log" && ! grep -q 99aa88bb "$SBX/calls.log"; then
  record PASS "setup_api_replaces_own_job_only"
else
  record FAIL "setup_api_replaces_own_job_only ($(tr '\n' ';' < "$SBX/calls.log" 2>/dev/null))"
fi
rm -rf "$SBX"

# 6) Sample mode never registers cron (stub hermes: the eval must not depend on the live cron list)
STUB="$(mktemp -d)"
printf '#!/usr/bin/env bash\necho "$*" >> "%s/calls.log"\nexit 0\n' "$STUB" > "$STUB/hermes"; chmod +x "$STUB/hermes"
out=$(PATH="$STUB:$PATH" HERMES_DEMAND_RADAR_MODE=sample HERMES_WORKDIR="$REPO" bash "$DIR/setup-demand-radar-cron.sh" --dry-run 2>&1 || true)
if [[ "$out" == *'등록하지 않습니다'* ]] && ! grep -q "cron create" "$STUB/calls.log" 2>/dev/null; then
  record PASS "sample_mode_no_cron"
else
  record FAIL "sample_mode_no_cron"
fi
rm -rf "$STUB"

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
