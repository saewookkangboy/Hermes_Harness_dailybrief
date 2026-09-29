#!/usr/bin/env bash
# Campaign launch graph eval — 샘플·모의 생성기 · 결정적 · 네트워크·Codex·광고 계정 호출 없음
#
# 검사: 그래프 경로 · 걸린 변형만 재작성 · 표시광고법/조건/링크/필수 문구 검수 ·
#       권장 글자 수는 차단 안 함 · 재시도 상한 · 브리프 검증 · 승인 전 패키지 없음 ·
#       승인 해시 가드 · 부분 승인 · CSV 일시중지·예산 열 없음 · 반려 · Codex 호출 모의 ·
#       광고 계정 쓰기 코드 없음 · 커맨더 라우팅(슬래시 /approve 미사용)
# Usage: ./scripts/campaign-launch-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Campaign Launch Graph Eval ==="
TMP_WS="$(mktemp -d)"
trap 'rm -rf "$TMP_WS"' EXIT

OUT=$(cd "$DIR" && HERMES_WORKDIR="$TMP_WS" HERMES_CAMPAIGN_NOTIFY= PYTHONPATH="$DIR" python3 - <<'PY'
import copy
import csv
import io
import json
import re
import subprocess
from datetime import date
from pathlib import Path
from lib import campaign_graph as CG

def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)

TODAY = date(2026, 9, 29)
ws = CG.workdir()
cfg = CG.load_config()
cfg["mode"] = "sample"
sent = []
CG.notify = lambda msg: sent.append(msg)          # 알림은 기록만
CG._record_cost = lambda text, cid: None           # 비용 원장 오염 방지
fixture = CG.REPO_ROOT / "tests/fixtures/campaign/brief_sample.yaml"

def brief_file(name, **over):
    import yaml
    b = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    for k, v in over.items():
        cur = b
        keys = k.split(".")
        for kk in keys[:-1]:
            cur = cur[kk]
        cur[keys[-1]] = v
    p = ws / f"{name}.yaml"
    p.write_text(yaml.safe_dump(b, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p

# 1) sample graph: 1회차에 [2] 근거 없는 표현 · [3] 제목 길이 → 2회차 재작성 → 승인 대기
p = brief_file("b1")
st = CG.start_campaign(str(p), cfg=cfg, today=TODAY)
check("graph_path_with_rewrite_loop", st["paths"][-1] == ["load_brief", "research", "copy", "review", "copy", "review", "approval", "human"])
rounds = {v["id"]: v["round"] for v in st["variants"]}
check("rewrites_only_failing_variants", rounds == {1: 1, 2: 2, 3: 2})
check("awaiting_approval", st["status"] == "awaiting_approval" and len([v for v in st["variants"] if v["status"] == "ready"]) == 3)
check("no_package_before_approval", not list((ws / cfg["outputs_dir"]).glob("*_launch.md")) and "package" not in st)
check("sample_mode_no_notify", sent == [])
card = CG.format_approval_card(st, cfg)
check("card_natural_language_approve", f"캠페인 승인 {st['id']}" in card and "/approve campaign" not in card)
check("card_shows_rewrite_history", "1회차 [2]" in card and "1회차 [3]" in card)

# 2) review rules
b = st["brief"]
rv = lambda **v: CG.review_variant({"id": 9, "angle": "", "primary_text": "", "headline": "웨비나", "description": "", **v}, b, cfg)
check("claim_without_evidence_blocked", rv(primary_text="국내 1위 웨비나")["hard"])
b2 = copy.deepcopy(b); b2["substantiated_claims"] = [{"claim": "만족도 1위", "source": "2025 설문 n=412"}]
r = CG.review_variant({"id": 9, "primary_text": "만족도 1위 웨비나", "headline": "웨비나", "description": ""}, b2, cfg)
check("claim_with_evidence_passes_with_note", not r["hard"] and r["notes"])
check("allow_phrase_not_flagged", not rv(primary_text="최고경영자가 직접 소개하는 웨비나")["hard"])
b3 = copy.deepcopy(b); b3["offer"]["conditions"] = ""
check("free_needs_conditions", CG.review_variant({"id": 9, "primary_text": "무료 웨비나", "headline": "웨비나"}, b3, cfg)["hard"])
check("url_in_copy_blocked", rv(primary_text="웨비나 https://x.com")["hard"])
check("placeholder_blocked", rv(primary_text="{{브랜드}} 웨비나")["hard"])
check("must_include_enforced", CG.review_variant({"id": 9, "primary_text": "안내", "headline": "안내"}, b, cfg)["hard"])
check("banned_word_blocked", rv(primary_text="마케팅 혁명 웨비나")["hard"])
long = rv(primary_text="웨비나", headline="웨비나" + "가" * 60)
check("length_is_soft_not_hard", long["soft"] and not long["hard"])

# 3) retry cap: soft-only 변형은 상한 뒤 승인으로, hard는 막힘
def gen_always(v_over):
    def g(state, cfg_, targets, round_no):
        ids = [t["id"] for t in targets] or [1, 2, 3]
        return [{"id": i, "angle": f"a{i}", "primary_text": f"웨비나 안내 {i}", "headline": f"웨비나 {i}", "description": "", **v_over} for i in ids]
    return g
st2 = CG.start_campaign(str(brief_file("b2", id="soft-only")), cfg=cfg, today=TODAY, generator=gen_always({"headline": "웨비나" + "나" * 50}))
check("soft_after_retries_goes_to_approval", st2["status"] == "awaiting_approval" and st2["attempts"] == cfg["copy"]["max_retries"] + 1)
st3 = CG.start_campaign(str(brief_file("b3", id="hard-only")), cfg=cfg, today=TODAY, generator=gen_always({"primary_text": "국내 1위 웨비나"}))
one = lambda state, cfg_, targets, round_no: [{"id": 1, "angle": "a", "primary_text": "웨비나 안내", "headline": "웨비나", "description": ""}]
st1 = CG.start_campaign(str(brief_file("b1b", id="too-few")), cfg=cfg, today=TODAY, generator=one)
check("too_few_variants_blocked", st1["status"] == "blocked" and st1["attempts"] == 1)
check("hard_after_retries_blocked", st3["status"] == "blocked" and st3["attempts"] == cfg["copy"]["max_retries"] + 1 and st3["paths"][-1][-1] == "blocked")

# 4) brief validation → load_brief에서 막힘
for name, over in {
    "http_landing": {"landing_url": "http://example.com"},
    "budget_typo": {"budget.daily_krw": 50000000},
    "end_before_start": {"schedule.end": "2026-10-01"},
    "bad_cta": {"cta": "BUY_EVERYTHING"},
}.items():
    s = CG.start_campaign(str(brief_file(f"x-{name}", id=f"x-{name.replace('_', '-')}", **over)), cfg=cfg, today=TODAY)
    check(f"brief_blocked_{name}", s["status"] == "blocked" and s["paths"][-1] == ["load_brief", "blocked"])

# 5) approval guards
p_hash = brief_file("b4", id="hash-guard")
CG.start_campaign(str(p_hash), cfg=cfg, today=TODAY)
p_hash.write_text(p_hash.read_text(encoding="utf-8").replace("50000", "500000"), encoding="utf-8")
try:
    CG.approve("hash-guard", cfg=cfg, today=TODAY); check("approve_rejects_changed_brief", False)
except CG.CampaignError:
    check("approve_rejects_changed_brief", True)
try:
    CG.approve(st["id"], [7], cfg=cfg, today=TODAY); check("approve_rejects_unknown_pick", False)
except CG.CampaignError:
    check("approve_rejects_unknown_pick", True)

done = CG.approve(st["id"], [1, 3], cfg=cfg, today=TODAY)
check("approve_runs_package_and_handoff", done["status"] == "packaged" and done["paths"][-1] == ["package", "handoff", "end"])
launch, csvp = Path(done["package"]["launch"]), Path(done["package"]["csv"])
check("sample_outputs_prefixed", launch.name.startswith("_sample_2026-09-29_campaign_") and csvp.exists())
rows = list(csv.reader(io.StringIO(csvp.read_text(encoding="utf-8-sig"))))
cols = cfg["package"]["columns"]
check("csv_header_from_config", rows[0] == list(cols.values()))
status_i = rows[0].index(cols["ad_status"])
check("csv_partial_approval_rows", [r[rows[0].index(cols["ad_name"])] for r in rows[1:]] == [f"{st['id']}_v1", f"{st['id']}_v3"])
check("csv_all_paused_no_budget", all(r[status_i] == "PAUSED" for r in rows[1:]) and not any("budget" in h.lower() for h in rows[0]))
md = launch.read_text(encoding="utf-8")
check("launch_has_manual_settings_and_handoff", "₩50,000" in md and "meta-fatigue" in md and "켜기 전 확인" in md)
try:
    CG.approve(st["id"], cfg=cfg, today=TODAY); check("double_approve_rejected", False)
except CG.CampaignError:
    check("double_approve_rejected", True)
try:
    CG.start_campaign(str(p), cfg=cfg, today=TODAY); check("rerun_packaged_needs_restart", False)
except CG.CampaignError:
    check("rerun_packaged_needs_restart", True)

CG.start_campaign(str(brief_file("b5", id="to-reject")), cfg=cfg, today=TODAY)
CG.reject("to-reject", "톤 수정", cfg=cfg)
try:
    CG.approve("to-reject", cfg=cfg, today=TODAY); check("rejected_cannot_approve", False)
except CG.CampaignError:
    check("rejected_cannot_approve", CG.load_state(cfg, "to-reject")["status"] == "rejected")
check("pending_lists_only_waiting", "soft-only" in CG.format_pending(cfg) and "to-reject" not in CG.format_pending(cfg))

# 6) codex generator (hermes-run 모의 · 네트워크 없음)
calls = []
def fake_run(cmd, **kw):
    calls.append((cmd, kw.get("env", {})))
    out = Path(re.search(r"이 파일에 저장하세요: (\S+)", cmd[1]).group(1))
    out.write_text('```json\n{"variants": [' + ",".join(
        '{"id": %d, "angle": "a", "primary_text": "웨비나 안내 %d", "headline": "웨비나 %d", "description": ""}' % (i, i, i) for i in (1, 2, 3)
    ) + "]}\n```", encoding="utf-8")
    return subprocess.CompletedProcess(cmd, 0, stdout="saved", stderr="")
import lib.loop_budget as LB
orig_run, orig_budget = subprocess.run, LB.check_loop_budget
subprocess.run = fake_run
LB.check_loop_budget = lambda: type("B", (), {"ok": True, "detail": ""})()
try:
    sc = CG.start_campaign(str(brief_file("b6", id="codex-mock")), cfg=cfg, mode="codex", today=TODAY)
finally:
    subprocess.run = orig_run
check("codex_mode_uses_hermes_run_with_codex", calls and calls[0][0][0].endswith("hermes-run.sh") and calls[0][1].get("HERMES_USE_CODEX") == "1")
check("codex_output_parsed_to_approval", sc["status"] == "awaiting_approval" and len(sc["variants"]) == 3)
check("codex_mode_notifies_card", any("캠페인 승인 대기" in m for m in sent))
LB.check_loop_budget = lambda: type("B", (), {"ok": False, "detail": "token cap exceeded"})()
try:
    sb = CG.start_campaign(str(brief_file("b7", id="budget-kill")), cfg=cfg, mode="codex", today=TODAY)
finally:
    LB.check_loop_budget = orig_budget
check("loop_budget_blocks_codex", sb["status"] == "blocked" and "예산" in sb.get("blocked_reason", ""))
check("parse_variants_tolerates_noise", len(CG.parse_variants('noise {"x":1} ```json\n{"variants":[{"id":1,"headline":"h","primary_text":"p"}]}\n``` tail')) == 1)

# 7) Config, state file and approval lock
import os, tempfile, time, threading
orig_cfg_path = CG.CONFIG_PATH
tmpd = Path(tempfile.mkdtemp())
cfg_ok = True
for path, text in ((tmpd / "absent.yaml", None), (tmpd / "broken.yaml", "campaign_launch:\n  review: [unclosed\n"), (tmpd / "nosection.yaml", "x: 1\n")):
    if text is not None:
        path.write_text(text, encoding="utf-8")
    CG.CONFIG_PATH = path
    try:
        CG.load_config(); cfg_ok = False
    except CG.ConfigError:
        pass
CG.CONFIG_PATH = orig_cfg_path
check("config_missing_or_broken_fails_loudly", cfg_ok)

sa = CG.start_campaign(str(brief_file("b8", id="atomic-save")), cfg=cfg, today=TODAY)
state_file = CG._state_path(cfg, "atomic-save")
before = state_file.read_text(encoding="utf-8")
orig_replace = os.replace
def boom(*a, **k):
    raise OSError("disk full")
os.replace = boom
try:
    try:
        CG.save_state(cfg, {**sa, "status": "blocked"})
    except OSError:
        pass
finally:
    os.replace = orig_replace
check("interrupted_save_keeps_previous_state", state_file.read_text(encoding="utf-8") == before and json.loads(before)["status"] == "awaiting_approval")

sl = CG.start_campaign(str(brief_file("b9", id="lock-test")), cfg=cfg, today=TODAY)
import fcntl
lock_fh = open(CG._state_path(cfg, "lock-test").with_suffix(".lock"), "w")
fcntl.flock(lock_fh, fcntl.LOCK_EX)
results = []
def worker():
    try:
        results.append(CG.approve("lock-test", cfg=cfg, today=TODAY)["status"])
    except CG.CampaignError as e:
        results.append(f"err:{e}")
t = threading.Thread(target=worker); t.start()
time.sleep(0.4)
waited = t.is_alive() and not results
fcntl.flock(lock_fh, fcntl.LOCK_UN); lock_fh.close()
t.join(10)
second = None
try:
    CG.approve("lock-test", cfg=cfg, today=TODAY)
except CG.CampaignError:
    second = "rejected"
check("approve_waits_for_lock_then_single_package", waited and results == ["packaged"] and second == "rejected")
PY
)
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  record "${line%% *}" "${line#* }"
done <<< "$OUT"

# 7) No ad-account writes: no Meta Graph endpoint or HTTP client in the campaign code
if grep -nE 'graph\.facebook\.com|urllib\.request|import requests|http\.client|/act_' \
    "$DIR/lib/campaign_graph.py" "$DIR/campaign-launch.py" >/dev/null; then
  record FAIL "no_ad_account_writes"
else
  record PASS "no_ad_account_writes"
fi

# 8) Commander routing: campaign messages go to auto (never the arg-less /approve quick command)
INTENTS=$(cd "$DIR" && PYTHONPATH="$DIR" python3 - <<'PY'
import importlib.util, sys
sys.argv = ["x"]
spec = importlib.util.spec_from_file_location("ha", "hermes-agent.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ok = (m.detect_intent("캠페인 승인 abc 1 3") == ("campaign-approve", "abc 1 3")
      and m.detect_intent("캠페인 반려 abc 톤") == ("campaign-reject", "abc 톤")
      and m.detect_intent("승인 linkedin") == ("approve", "linkedin"))
print("PASS" if ok else "FAIL")
PY
)
record "$INTENTS" "agent_intents"

route_ok=1
eval "$(sed -n '/^is_campaign_command()/,/^}/p' "$DIR/telegram-pipeline.sh")"
is_campaign_command "캠페인 승인 marketing-automation-oct" || route_ok=0
is_campaign_command "캠페인승인 abc" || route_ok=0
is_campaign_command "승인 linkedin" && route_ok=0
is_campaign_command "/approve" && route_ok=0
[[ $route_ok -eq 1 ]] && record PASS "pipeline_routes_campaign_before_personal" || record FAIL "pipeline_routes_campaign_before_personal"
grep -q 'never qc approve' "$REPO/config/commander-easytool.yaml" && grep -q '캠페인 승인' "$REPO/config/telegram-routing.yaml" \
  && grep -q '캠페인 승인' "$REPO/config/slack-routing.yaml" && record PASS "commander_prompts_route_campaign" || record FAIL "commander_prompts_route_campaign"

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
