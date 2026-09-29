#!/usr/bin/env bash
# Slash-command safety eval — 결정적, 실제 승인·리서치·Notion 실행 없음
#
# Hermes 게이트웨이의 exec quick command(슬래시)는 뒤에 붙인 글자를 넘기지 않습니다
# (upstream gateway/run_inbound.py `_hm_run_exec_quick_command(command, exec_cmd)`).
# 그래서 `/approve linkedin`은 예전에 `approve all`로, `/research RAG`는 키워드 없는
# 전체 리서치로 실행됐습니다. 이 eval은 인자 없는 슬래시가 조회·안내만 하는지 고정합니다.
#
# Usage: ./scripts/slash-commands-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

echo "=== Slash Commands Eval ==="
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Sandbox: real telegram-pipeline.sh + lib, stubbed side-effect scripts that only log their args
mkdir -p "$TMP/scripts"
cp "$DIR/telegram-pipeline.sh" "$TMP/scripts/"
ln -s "$DIR/lib" "$TMP/scripts/lib"
for s in hermes-agent.sh run-research-brief.sh run-content-package.sh run-newsletter.sh archive-to-notion.sh \
         telegram-notify.sh slack-notify.sh validate-output.sh run-keyword-research.sh; do
  printf '#!/usr/bin/env bash\necho "CALLED %s $*" >> "%s/calls.log"\n' "$s" "$TMP" > "$TMP/scripts/$s"
  chmod +x "$TMP/scripts/$s"
done
mkdir -p "$TMP/home/.hermes/logs"
run_qc() { : > "$TMP/calls.log"; HOME="$TMP/home" TELEGRAM_CHAT_ID= HERMES_WORKDIR="$TMP" bash "$TMP/scripts/telegram-pipeline.sh" qc "$@" 2>&1 || true; }

# 1) /approve (no args arrive) → pending view + usage, never approve
out=$(run_qc approve)
calls=$(cat "$TMP/calls.log")
[[ "$calls" == *"hermes-agent.sh pending"* && "$calls" != *" approve"* ]] \
  && record PASS "slash_approve_is_view_only" || record FAIL "slash_approve_is_view_only ($calls)"
[[ "$out" == *"승인 linkedin"* ]] && record PASS "slash_approve_shows_usage" || record FAIL "slash_approve_shows_usage"

# 2) /research (no args arrive) → status + usage, never the full research run
out=$(run_qc research)
calls=$(cat "$TMP/calls.log")
[[ "$calls" != *"run-research-brief.sh"* && "$calls" != *"run-content-package.sh"* ]] \
  && record PASS "slash_research_does_not_run" || record FAIL "slash_research_does_not_run ($calls)"
[[ "$out" == *"리서치 <키워드>"* ]] && record PASS "slash_research_shows_usage" || record FAIL "slash_research_shows_usage"

# 3) Natural-language approvals keep working; bare 승인 only lists
AGENT=$(cd "$DIR" && PYTHONPATH="$DIR" python3 - <<'PY'
import importlib.util, io, sys, contextlib
from argparse import Namespace
sys.argv = ["x"]
spec = importlib.util.spec_from_file_location("ha", "hermes-agent.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
calls = []
m.approve_channels = lambda stamp, ch: calls.append(("approve", list(ch))) or {"approved_channels": list(ch)}
m.execute_approved_publish = lambda stamp, ch=None: {"published": []}
m.format_approval_card = lambda stamp, data=None: ""
m._commander_notify = lambda msg: None
m.record_action = lambda *a, **k: None
m._trace_intent = lambda *a, **k: None
def auto(text):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m.cmd_auto(Namespace(text=text, date="2099-01-01", session="eval", json=False))
    return buf.getvalue()
out = auto("승인")
print("PASS bare_approve_lists_only" if not calls and "승인 linkedin" in out else f"FAIL bare_approve_lists_only {calls}")
calls.clear(); auto("승인 linkedin")
print("PASS nl_approve_channel" if calls == [("approve", ["linkedin"])] else f"FAIL nl_approve_channel {calls}")
calls.clear(); auto("승인 all")
print("PASS nl_approve_all_explicit" if calls == [("approve", ["all"])] else f"FAIL nl_approve_all_explicit {calls}")
PY
)
while IFS= read -r line; do [[ -n "$line" ]] && record "${line%% *}" "${line#* }"; done <<< "$AGENT"

# 4) User-facing cards no longer tell people to type "/approve <channel>"
if grep -nE '"[^"]*/approve (linkedin|newsletter|all)' "$DIR/lib/publish_gate.py" >/dev/null; then
  record FAIL "cards_use_natural_language"
else
  record PASS "cards_use_natural_language"
fi

# 5) Commander prompts route argument-bearing requests to auto
ok=1
for f in telegram-routing slack-routing playmcp-routing; do
  grep -q 'Slash never carries arguments' "$REPO/config/$f.yaml" || ok=0
done
grep -q 'slash drops args' "$REPO/config/commander-easytool.yaml" || ok=0
[[ $ok -eq 1 ]] && record PASS "commander_prompts_updated" || record FAIL "commander_prompts_updated"

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
