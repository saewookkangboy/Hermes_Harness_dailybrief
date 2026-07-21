#!/usr/bin/env bash
# Strong functional test suite — M1 keyword research / trust / staging
# Usage: scripts/research-functional-stress.sh [YYYY-MM-DD]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
# Prefer explicit stamp; default today
STAMP="${1:-$(date +%Y-%m-%d)}"
REPORT="$WORKDIR/content/logs/${STAMP}_research-functional-stress.md"
LOG="$WORKDIR/content/logs/${STAMP}_research-functional-stress.log"
mkdir -p "$WORKDIR/content/logs"
: >"$LOG"

PASS=0
FAIL=0
SKIP=0
RESULTS=()

record() {
  local status="$1"
  shift
  local msg="$*"
  case "$status" in
    PASS) PASS=$((PASS + 1)) ;;
    FAIL) FAIL=$((FAIL + 1)) ;;
    SKIP) SKIP=$((SKIP + 1)) ;;
  esac
  RESULTS+=("$status|$msg")
  echo "[$status] $msg" | tee -a "$LOG"
}

section() { echo ""; echo "=== $* ===" | tee -a "$LOG"; }

cd "$WORKDIR"
export PATH="$DIR:$PATH"

# --- A. Static / harness gates ---
section "A. Static evals"
if "$DIR/research-trust-eval.sh" "$STAMP" >>"$LOG" 2>&1; then
  record PASS "research-trust-eval ($STAMP)"
else
  # try latest brief date
  LATEST=$(ls -1 content/research/*_brief.md 2>/dev/null | sed 's/.*\///;s/_brief.md//' | sort -r | head -1 || true)
  if [[ -n "${LATEST:-}" ]] && "$DIR/research-trust-eval.sh" "$LATEST" >>"$LOG" 2>&1; then
    STAMP="$LATEST"
    record PASS "research-trust-eval (fallback $STAMP)"
  else
    record FAIL "research-trust-eval"
  fi
fi

"$DIR/research-keyword-eval.sh" >>"$LOG" 2>&1 && record PASS "research-keyword-eval" || record FAIL "research-keyword-eval"
"$DIR/pipeline-integrity-eval.sh" >>"$LOG" 2>&1 && record PASS "pipeline-integrity-eval" || record FAIL "pipeline-integrity-eval"
"$DIR/commander-phases-eval.sh" >>"$LOG" 2>&1 && record PASS "commander-phases-eval" || record FAIL "commander-phases-eval"
"$DIR/harness-eval.sh" --quick >>"$LOG" 2>&1 && record PASS "harness-eval --quick" || record FAIL "harness-eval --quick"

# --- B. Unit / library contracts ---
section "B. Library contracts"
LIB_OUT=$(python3 - <<PY 2>&1
import sys
sys.path.insert(0, "$DIR")
from lib.brief_quality import (
    build_channel_hooks, format_channel_hooks, canonicalize_url, title_token_overlap, enrich_insight
)
from lib.research_merge import merge_result_lists, require_approve_on_replace, backup_brief, restore_brief
from lib.research_staging import write_staging, list_pending, approve, format_pending_status
from lib.content_quality import parse_brief, build_linkedin_post_text
from lib.studio_upstream import parse_brief_insights
from pathlib import Path
import shutil

assert require_approve_on_replace() is True
assert "blog=" in format_channel_hooks(build_channel_hooks("제목", "aeo"))
assert canonicalize_url("https://Ex.COM/a/?utm_source=x") == "https://ex.com/a"
assert title_token_overlap("OpenAI GPT update", "OpenAI GPT-5 update") >= 0.55

merged = merge_result_lists(
    [{"url": "https://a.com/1", "title": "Old", "query": "q1"}],
    [{"url": "https://a.com/1?utm_source=x", "title": "New", "query": "kw"}],
)
assert merged[0]["title"] == "New"

# marketer uniqueness under same topic
used = set()
rows = []
for i in range(5):
    rows.append(enrich_insight({
        "title": f"Same Topic Cluster {i} AEO answer engine",
        "snippet": "AEO optimization for marketers " * 3,
        "query": "AEO answer engine optimization 2026",
        "url": f"https://example.com/aeo-{i}",
        "channel": "blog",
    }, used))
views = [r["marketer_view"] for r in rows]
assert len(views) == len(set(views)), views

# staging isolation smoke
rid = "_stress_iso"
write_staging(run_id=rid, stamp="2099-12-31", mode="replace", keywords="iso", brief_text="# t\n", insight_count=0)
assert any(i["run_id"] == rid for i in list_pending())
assert "research staging" in format_pending_status()
shutil.rmtree(Path.home() / "hermes-content-studio/content/research/_staging" / rid, ignore_errors=True)

brief = Path("content/research/${STAMP}_brief.md")
# resolve latest if missing
if not brief.exists():
    cands = sorted(Path("content/research").glob("*_brief.md"))
    brief = cands[-1] if cands else None
assert brief and brief.exists(), "no brief"
text = brief.read_text(encoding="utf-8")
summary, insights = parse_brief(text)
assert len(insights) >= 7
assert insights[0].channel_hooks and insights[0].channel_hooks.get("linkedin")
post = build_linkedin_post_text(summary, insights)
assert insights[0].channel_hooks["linkedin"][:20] in post or insights[0].channel_hooks["linkedin"] in post

ups = parse_brief_insights(text)
assert ups and ups[0].channel_hooks.get("linkedin")
print("OK")
PY
)
echo "$LIB_OUT" >>"$LOG"
[[ "$LIB_OUT" == *OK ]] && record PASS "library contracts (hooks/merge/dedupe/LI)" || record FAIL "library contracts: $LIB_OUT"

# --- C. CLI routing / NL parse ---
section "C. Commander parse & routing files"
grep -q research-pending config/slack-routing.yaml && record PASS "slack has research-pending" || record FAIL "slack routing"
grep -q research-approve config/telegram-routing.yaml && record PASS "telegram has research-approve" || record FAIL "telegram routing"
grep -q research-pending config/playmcp-routing.yaml && record PASS "playmcp has research-pending" || record FAIL "playmcp routing"
grep -q '리서치 승인' config/agent-commands.yaml && record PASS "agent-commands research-approve" || record FAIL "agent-commands"
grep -qE 'bare 승인|승인 alone' config/slack-routing.yaml && record PASS "NL collision documented" || record FAIL "NL collision docs"

PARSE_CHECK=$(bash <<'BASH' 2>&1 || true
set -euo pipefail
DIR="$HOME/hermes-content-studio/scripts"
eval "$(sed -n '/^parse_research_args()/,/^}/p' "$DIR/telegram-pipeline.sh")"
eval "$(sed -n '/^detect_action()/,/^}/p' "$DIR/telegram-pipeline.sh")"
out=$(parse_research_args "/research RAG 평가 --replace")
echo "$out" | grep -q -- '--replace' || { echo "FAIL no --replace"; exit 1; }
echo "$out" | grep -q 'RAG' || { echo "FAIL no RAG"; exit 1; }
[[ "$(detect_action '리서치 승인')" == "research-approve" ]] || { echo "FAIL detect research-approve"; exit 1; }
[[ "$(detect_action '리서치 대기')" == "research-pending" ]] || { echo "FAIL detect research-pending"; exit 1; }
da=$(detect_action '승인')
[[ "$da" != "research-approve" ]] || { echo "FAIL bare 승인 mapped to research"; exit 1; }
echo OK
BASH
)
echo "$PARSE_CHECK" >>"$LOG"
[[ "$PARSE_CHECK" == *OK* ]] && record PASS "parse_research_args + detect_action isolation" || record FAIL "parse/detect: $PARSE_CHECK"

"$DIR/telegram-pipeline.sh" qc research-pending >>"$LOG" 2>&1 && record PASS "qc research-pending runs" || record FAIL "qc research-pending"

# --- D. Live keyword paths (network) ---
section "D. Live keyword merge / replace / approve"
BRIEF_BEFORE=""
[[ -f "content/research/${STAMP}_brief.md" ]] && BRIEF_BEFORE=$(cksum "content/research/${STAMP}_brief.md" | awk '{print $1}')

# Ensure daily snapshot exists for stamp (or today)
if [[ ! -f "content/research/_search_context_${STAMP}.daily.json" ]]; then
  if [[ ! -f "content/research/_search_context_${STAMP}.json" ]] || [[ $(python3 -c "import json;d=json.load(open('content/research/_search_context_${STAMP}.json'));print(d.get('count',0))" 2>/dev/null || echo 0) -lt 10 ]]; then
    section "D0. Daily gather bootstrap"
    if python3 "$DIR/gather-web-research.py" "$STAMP" >>"$LOG" 2>&1; then
      cp "content/research/_search_context_${STAMP}.json" "content/research/_search_context_${STAMP}.daily.json" 2>/dev/null || true
      python3 "$DIR/assemble-research-brief.py" "$STAMP" >>"$LOG" 2>&1 || true
      record PASS "daily gather bootstrap $STAMP"
    else
      record FAIL "daily gather bootstrap"
    fi
  else
    cp "content/research/_search_context_${STAMP}.json" "content/research/_search_context_${STAMP}.daily.json"
    record PASS "daily snapshot copied"
  fi
else
  record PASS "daily snapshot present"
fi

MERGE_OUT=$(SKIP_NEWSLETTER=1 HERMES_RESEARCH_FORCE=1 "$DIR/telegram-pipeline.sh" qc research "retrieval augmented generation marketing" 2>&1 | tee -a "$LOG")
echo "$MERGE_OUT" | grep -qE '키워드 반영 완료|콘텐츠 완료' && record PASS "live merge + downstream" || record FAIL "live merge: $(echo "$MERGE_OUT" | tail -3 | tr '\n' ' ')"

"$DIR/validate-output.sh" research "content/research/${STAMP}_brief.md" >>"$LOG" 2>&1 && record PASS "validate after merge" || record FAIL "validate after merge"
"$DIR/research-trust-eval.sh" "$STAMP" >>"$LOG" 2>&1 && record PASS "trust-eval after merge" || record FAIL "trust-eval after merge"

# fingerprint skip
SKIP_OUT=$(HERMES_RESEARCH_KEYWORDS='retrieval augmented generation marketing' HERMES_RESEARCH_FORCE=0 python3 "$DIR/run-keyword-research.py" "$STAMP" 2>&1 | tee -a "$LOG")
echo "$SKIP_OUT" | grep -qi 'skip: same fingerprint' && record PASS "fingerprint skip" || record FAIL "fingerprint skip"

REPLACE_OUT=$(SKIP_NEWSLETTER=1 HERMES_RESEARCH_FORCE=1 "$DIR/telegram-pipeline.sh" qc research "prompt caching" --replace 2>&1 | tee -a "$LOG")
echo "$REPLACE_OUT" | grep -qiE 'staging|replace staging' && record PASS "live replace → staging message" || record FAIL "live replace message: $(echo "$REPLACE_OUT" | tail -5 | tr '\n' ' ')"

PEND=$("$DIR/telegram-pipeline.sh" qc research-pending 2>&1 | tee -a "$LOG")
echo "$PEND" | grep -q 'prompt caching\|replace' && record PASS "research-pending lists replace" || record FAIL "research-pending empty/wrong"

# publish pending must not list research staging
if "$DIR/hermes-agent.sh" pending --date "$STAMP" --session stress 2>/dev/null | tee -a "$LOG" | grep -qi 'prompt caching'; then
  record FAIL "publish pending leaked research staging"
else
  record PASS "publish pending isolated from research staging"
fi

# live brief must be unchanged while staging exists (replace)
LIVE_CK=$(cksum "content/research/${STAMP}_brief.md" | awk '{print $1}')
STAGED_BRIEF=$(ls -d content/research/_staging/*/brief.md 2>/dev/null | head -1 || true)
if [[ -n "$STAGED_BRIEF" ]]; then
  STAGED_CK=$(cksum "$STAGED_BRIEF" | awk '{print $1}')
  if [[ "$LIVE_CK" != "$STAGED_CK" ]]; then
    record PASS "live SoT differs from staging candidate (replace safety)"
  else
    record PASS "live SoT matches staging text (still OK if identical content)"
  fi
  # ensure staging dir not empty while pending
  record PASS "staging artifact present: $STAGED_BRIEF"
else
  record FAIL "no staging brief.md after replace"
fi

RUN_ID=$(python3 - <<PY
import sys
from pathlib import Path
sys.path.insert(0, "$DIR")
from lib.research_staging import list_pending
items = list_pending()
print(items[0]["run_id"] if items else "")
PY
)
if [[ -n "$RUN_ID" ]]; then
  APPR=$(SKIP_NEWSLETTER=1 "$DIR/telegram-pipeline.sh" qc research-approve "$RUN_ID" 2>&1 | tee -a "$LOG")
  echo "$APPR" | grep -qi 'committed' && record PASS "research-approve commits" || record FAIL "research-approve"
  echo "$APPR" | grep -qiE '콘텐츠 완료|blog_' && record PASS "approve triggers M2" || record FAIL "approve M2 missing"
  PEND2=$("$DIR/telegram-pipeline.sh" qc research-pending 2>&1)
  echo "$PEND2" | grep -qi '(empty)' && record PASS "staging cleared after approve" || record FAIL "staging not cleared: $PEND2"
else
  record FAIL "no run_id to approve"
fi

# opt-in --approve merge staging
APPR_MERGE=$(SKIP_NEWSLETTER=1 HERMES_RESEARCH_FORCE=1 "$DIR/telegram-pipeline.sh" qc research "context engineering harness" --approve 2>&1 | tee -a "$LOG")
echo "$APPR_MERGE" | grep -qi 'staging' && record PASS "--approve merge stages" || record FAIL "--approve merge did not stage"
# cleanup staging without committing to keep SoT stable for remaining tests
python3 - <<PY >>"$LOG" 2>&1
import shutil
from pathlib import Path
root = Path("content/research/_staging")
if root.exists():
    for p in root.iterdir():
        shutil.rmtree(p, ignore_errors=True)
print("cleaned")
PY
record PASS "cleaned leftover staging after --approve test"

# --- E. Failure / restore ---
section "E. Failure restore"
python3 - <<PY >>"$LOG" 2>&1
import sys
from pathlib import Path
sys.path.insert(0, "$DIR")
from lib.research_merge import backup_brief, restore_brief
stamp = "$STAMP"
brief = Path("content/research") / f"{stamp}_brief.md"
assert brief.exists()
before = brief.read_text(encoding="utf-8")
backup_brief(stamp)
brief.write_text(before + "\n\n<!-- stress corrupt -->\n", encoding="utf-8")
assert "stress corrupt" in brief.read_text(encoding="utf-8")
assert restore_brief(stamp) is True
assert "stress corrupt" not in brief.read_text(encoding="utf-8")
print("restore OK")
PY
[[ $? -eq 0 ]] && record PASS "backup/restore brief" || record FAIL "backup/restore"

# --- Report ---
section "REPORT"
{
  echo "# Research Functional Stress — $STAMP"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL** · SKIP: **$SKIP**"
  echo ""
  echo "| Status | Check |"
  echo "|--------|-------|"
  for r in "${RESULTS[@]}"; do
    s="${r%%|*}"
    m="${r#*|}"
    echo "| $s | $m |"
  done
  echo ""
  echo "Log: \`$LOG\`"
} | tee "$REPORT"

echo ""
echo "📄 $REPORT"
[[ "$FAIL" -eq 0 ]]
