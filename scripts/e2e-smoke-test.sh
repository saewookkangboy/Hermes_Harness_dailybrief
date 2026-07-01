#!/usr/bin/env bash
# Hermes Content Studio — E2E 사용성·성능 스모크 테스트
#
# Usage:
#   ./e2e-smoke-test.sh              # 파이프라인 + 검증 (기본)
#   ./e2e-smoke-test.sh --telegram   # Telegram 알림·post-sync 포함
#   ./e2e-smoke-test.sh --full       # 강의 + Notion 아카이브 포함
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
DATE="$(date +%Y-%m-%d)"
TELEGRAM=0
FULL=0

for arg in "$@"; do
  case "$arg" in
    --telegram) TELEGRAM=1 ;;
    --full) FULL=1 ;;
    --help|-h)
      echo "Usage: $0 [YYYY-MM-DD] [--telegram] [--full]"
      exit 0
      ;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])
      DATE="$arg"
      ;;
  esac
done

PASS=0
FAIL=0
WARN=0
RESULTS=()

pass() { echo "✅ $1"; PASS=$((PASS + 1)); RESULTS+=("PASS:$1"); }
fail() { echo "❌ $1"; FAIL=$((FAIL + 1)); RESULTS+=("FAIL:$1"); }
warn() { echo "⚠️  $1"; WARN=$((WARN + 1)); RESULTS+=("WARN:$1"); }

time_stage() {
  local label="$1"
  shift
  local start end elapsed
  start=$(date +%s)
  if "$@"; then
    end=$(date +%s)
    elapsed=$(( end - start ))
    pass "$label (${elapsed}s)"
    echo "$label:$elapsed"
  else
    fail "$label"
    return 1
  fi
}

echo "=== E2E Smoke Test — $DATE ==="
echo ""

echo "--- 1/6 Harness 구조 ---"
if "$DIR/harness-eval.sh" --quick >/dev/null 2>&1; then
  pass "harness-eval --quick"
else
  fail "harness-eval --quick"
fi

echo ""
echo "--- 2/6 헬스체크 ---"
if "$DIR/health-check.sh" >/tmp/e2e-health.log 2>&1; then
  pass "health-check"
else
  HC_FAIL=$(grep -c "^❌" /tmp/e2e-health.log || echo 0)
  if [[ "$HC_FAIL" -eq 0 ]]; then
    warn "health-check (선택 항목 경고만)"
  else
    fail "health-check ($HC_FAIL failures)"
  fi
fi

echo ""
echo "--- 3/6 결정적 파이프라인 ---"
PIPE_START=$(date +%s)
SKIP_INIT=1 SKIP_LECTURE=1 SKIP_NOTION_ARCHIVE=1 "$DIR/run-pipeline.sh" "$DATE" >/tmp/e2e-pipeline.log 2>&1 || true
PIPE_END=$(date +%s)
PIPE_ELAPSED=$(( PIPE_END - PIPE_START ))

BRIEF="$WORKDIR/content/research/${DATE}_brief.md"
NL_SCORES="$WORKDIR/content/newsletter/${DATE}_newsletter_subject-scores.json"
if [[ -f "$BRIEF" ]]; then
  if (( PIPE_ELAPSED <= 70 )); then
    pass "파이프라인 ${PIPE_ELAPSED}s (SLA ≤70s, M1+M2+M2b)"
  else
    warn "파이프라인 ${PIPE_ELAPSED}s (SLA 70s 초과)"
  fi
else
  fail "파이프라인 — brief 미생성"
fi
if [[ -f "$NL_SCORES" ]]; then
  pass "파이프라인 newsletter 산출"
else
  fail "파이프라인 — newsletter 미생성"
fi

echo ""
echo "--- 3b/7 Supervised cron (L2) — config · stages ---"
CRON_DRY=$(HERMES_CRON_SUPERVISED_DRY_RUN=1 "$DIR/cron-supervised-pipeline.sh" 2>&1) || true
if echo "$CRON_DRY" | grep -q "HERMES_CRON_HUMANIZE=1"; then
  pass "cron default HERMES_CRON_HUMANIZE=1"
else
  fail "cron default HERMES_CRON_HUMANIZE≠1"
fi
if echo "$CRON_DRY" | grep -q "SKIP_NEWSLETTER=0"; then
  pass "cron default SKIP_NEWSLETTER=0 (M2b ON)"
else
  fail "cron default SKIP_NEWSLETTER≠0"
fi
HANDOFF="$WORKDIR/.harness/handoffs/${DATE}_supervised-pipeline.json"
_handoff_ok() {
  [[ -f "$HANDOFF" ]] || return 1
  python3 -c "
import json, sys
from pathlib import Path
d = json.loads(Path('$HANDOFF').read_text(encoding='utf-8'))
ids = {s.get('id') for s in d.get('stages', [])}
need = {'VOICE', 'HUMANIZE', 'NATURALNESS'}
missing = need - ids
if missing:
    raise SystemExit('missing: ' + ','.join(sorted(missing)))
for s in d.get('stages', []):
    if s.get('id') in need and s.get('status') not in ('PASS', 'WARN'):
        raise SystemExit(s.get('id') + ' status ' + str(s.get('status')))
" 2>/dev/null
}
if _handoff_ok; then
  pass "supervised handoff VOICE/HUMANIZE/NATURALNESS"
else
  echo "  ↻ handoff 갱신 — cron-supervised-pipeline (SKIP_NOTION)"
  HERMES_CRON_SKIP_NOTION=1 "$DIR/cron-supervised-pipeline.sh" "$DATE" >/tmp/e2e-supervised-refresh.log 2>&1 || true
  if _handoff_ok; then
    pass "supervised handoff refreshed"
  else
    fail "supervised handoff stages"
  fi
fi

echo ""
echo "--- 3c/7 Humanize LLM · Loop budget (wiring) ---"
if "$DIR/humanize-llm-eval.sh" "$DATE" >/tmp/e2e-humanize-llm.log 2>&1; then
  pass "humanize-llm-eval (wiring)"
else
  fail "humanize-llm-eval (wiring)"
fi
if "$DIR/loop-budget-eval.sh" >/tmp/e2e-loop-budget.log 2>&1; then
  pass "loop-budget-eval"
else
  fail "loop-budget-eval"
fi
if "$DIR/playmcp-routing-e2e.sh" >/tmp/e2e-playmcp-routing.log 2>&1; then
  pass "playmcp-routing-e2e (wiring)"
else
  fail "playmcp-routing-e2e (wiring)"
fi

echo ""
echo "--- 4/7 산출물 품질 검증 ---"
for spec in \
  "research:$BRIEF" \
  "blog:$WORKDIR/content/blog/${DATE}_blog_" \
  "instagram:$WORKDIR/content/instagram/${DATE}_instagram_" \
  "linkedin:$WORKDIR/content/linkedin/${DATE}_linkedin_" \
  "newsletter:$WORKDIR/content/newsletter/${DATE}_newsletter_" \
  "newsletter-html:$WORKDIR/content/newsletter/${DATE}_newsletter_" \
  "newsletter-context:$WORKDIR/content/packages/${DATE}_newsletter-context.md" \
  "newsletter-paste:$WORKDIR/content/packages/${DATE}_newsletter-paste.md" \
  "newsletter-subject-scores:$NL_SCORES"; do
  type="${spec%%:*}"
  path_prefix="${spec#*:}"
  if [[ "$path_prefix" == *"_" && "$path_prefix" != *.md && "$path_prefix" != *.html ]]; then
    case "$type" in
      newsletter) found=$(ls "$path_prefix"*.md 2>/dev/null | head -1 || true) ;;
      newsletter-html) found=$(ls "$path_prefix"*.html 2>/dev/null | head -1 || true) ;;
      *) found=$(ls "$path_prefix"*.html "$path_prefix"*.md 2>/dev/null | head -1 || true) ;;
    esac
    if [[ -n "$found" ]] && "$DIR/validate-output.sh" "$type" "$found" >/dev/null 2>&1; then
      pass "validate $type"
    else
      fail "validate $type — $path_prefix*"
    fi
  else
    if "$DIR/validate-output.sh" "$type" "$path_prefix" >/dev/null 2>&1; then
      pass "validate $type"
    else
      fail "validate $type"
    fi
  fi
done

if [[ "$FULL" -eq 1 ]]; then
  echo ""
  echo "--- 5a/6 강의 슬라이드 (basic) ---"
  LEC_START=$(date +%s)
  if SKIP_INIT=1 "$DIR/run-lecture-slides.sh" --from-brief "$DATE" >/tmp/e2e-lecture.log 2>&1; then
    LEC_ELAPSED=$(( $(date +%s) - LEC_START ))
    pass "강의 슬라이드 ${LEC_ELAPSED}s"
  else
    fail "강의 슬라이드"
  fi
fi

if [[ "$FULL" -eq 1 || "$TELEGRAM" -eq 1 ]]; then
  echo ""
  echo "--- 5b/6 Notion 아카이브 ---"
  ARCH_START=$(date +%s)
  ARCH_ARGS=("$DATE" --force)
  CHAT="${TELEGRAM_CHAT_ID:-}"
  [[ -z "$CHAT" && -f "$HOME/.hermes/.env" ]] && CHAT=$(grep -E '^TELEGRAM_ALLOWED_USERS=' "$HOME/.hermes/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
  [[ -n "$CHAT" && "$TELEGRAM" -eq 1 ]] && ARCH_ARGS+=(--telegram-chat "$CHAT")
  if "$DIR/archive-to-notion.sh" "${ARCH_ARGS[@]}" >/tmp/e2e-notion.log 2>&1; then
    ARCH_ELAPSED=$(( $(date +%s) - ARCH_START ))
    COUNT=$(grep -o '"count": [0-9]*' /tmp/e2e-notion.log | tail -1 | grep -o '[0-9]*' || echo "?")
    if [[ -n "$COUNT" && "$COUNT" != "?" ]] && (( COUNT >= 8 )); then
      pass "Notion 카테고리 ${COUNT}건 (newsletter+paste 포함)"
    elif [[ -n "$COUNT" && "$COUNT" != "?" ]]; then
      warn "Notion ${COUNT}건 (<8, newsletter_paste 누락 가능)"
    fi
    if (( ARCH_ELAPSED <= 120 )); then
      pass "Notion 아카이브 ${ARCH_ELAPSED}s (${COUNT}건)"
    else
      warn "Notion 아카이브 ${ARCH_ELAPSED}s (SLA 120s 초과, ${COUNT}건)"
    fi
  else
    fail "Notion 아카이브"
  fi
fi

if [[ "$TELEGRAM" -eq 1 ]]; then
  echo ""
  echo "--- 6/6 Telegram I/O ---"
  if [[ -z "${CHAT:-}" ]]; then
    CHAT=$(cd "$DIR" && source "$HOME/.hermes/.env" 2>/dev/null; echo "${TELEGRAM_CHAT_ID:-${TELEGRAM_ALLOWED_USERS:-}}")
  fi
  if [[ -z "${CHAT:-}" ]]; then
    warn "TELEGRAM_CHAT_ID 미설정 — telegram-notify/post-sync 스킵"
  else
    QC_START=$(date +%s)
    if DATE="$DATE" TELEGRAM_CHAT_ID="$CHAT" "$DIR/telegram-pipeline.sh" qc status >/dev/null 2>&1; then
      pass "telegram-pipeline qc status"
    else
      fail "telegram-pipeline qc status"
    fi
    if "$DIR/telegram-notify.sh" "$CHAT" "[🧪 E2E] smoke test $DATE — notify OK" >/dev/null 2>&1; then
      pass "telegram-notify (${CHAT})"
    else
      fail "telegram-notify"
    fi
    if grep -q 'telegram-pipeline.sh qc pipeline' "$HOME/.hermes/config.yaml" 2>/dev/null; then
      pass "Hermes quick_commands (/pipeline)"
    else
      warn "quick_commands 미설정 — setup-telegram-routing.sh 실행"
    fi
  fi
fi

echo ""
echo "=== E2E 결과: ✅ $PASS / ❌ $FAIL / ⚠️ $WARN ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
