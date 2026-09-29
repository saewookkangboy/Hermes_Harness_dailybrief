#!/usr/bin/env bash
# Commander free-text routing regression eval — 결정적, 실행 없음
#
# 2026-09-29 감사에서 확인된 부작용 경로를 고정합니다:
#   - 미매칭 메시지("고마워!")가 전체 파이프라인을 실행
#   - "노션 … 확인"이 archive-to-notion.sh --force (sync)로 라우팅
#   - "받은편지함" 오타로 메일 요청이 파이프라인으로 감
#   - 자연어로 추론된 automate가 Cursor CLI를 자동 실행
#
# 라우팅 함수 본문만 추출해 실행하므로 파이프라인·Codex·Notion은 호출되지 않습니다.
# Usage: ./scripts/router-eval.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
export LC_ALL="${LC_ALL:-C.UTF-8}"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

eval "$(sed -n '/^detect_personal()/,/^}/p' "$DIR/telegram-pipeline.sh")"
eval "$(sed -n '/^detect_action()/,/^}/p' "$DIR/telegram-pipeline.sh")"
eval "$(sed -n '/^detect_task_type()/,/^}/p' "$DIR/telegram-custom.sh")"
eval "$(sed -n '/^is_explicit_automate()/,/^}/p' "$DIR/telegram-custom.sh")"

route() {
  if detect_personal "$1"; then echo "personal:$(detect_task_type "$1")"
  else echo "pipeline:$(detect_action "$1")"; fi
}

expect() {
  local msg="$1" want="$2" got
  got=$(route "$msg")
  [[ "$got" == "$want" ]] && record PASS "route \"$msg\" → $got" || record FAIL "route \"$msg\" → $got (want $want)"
}

expect_not() {
  local msg="$1" bad="$2" got
  got=$(route "$msg")
  [[ "$got" != "$bad" ]] && record PASS "route \"$msg\" → $got (not $bad)" || record FAIL "route \"$msg\" → $got"
}

echo "=== Router Eval ==="
# Unmatched free text must not run anything
expect "고마워!" "pipeline:help"
expect_not "오늘 성과 어땠어?" "pipeline:pipeline"
# Read-only Notion checks must not hit sync (--force write)
expect "노션에 어제 브리프 올라갔는지 확인" "pipeline:notion-status"
expect "노션 상태 알려줘" "pipeline:notion-status"
expect "노션에 다시 올려줘" "pipeline:sync"
expect "노션 동기화 상태 알려줘" "pipeline:notion-status"
expect "노션 중복 페이지 있어?" "pipeline:notion-status"
expect "콘텐츠 중복 확인해줘" "pipeline:content"
# Inbox typo
expect "받은편지함 정리해줘" "personal:mail"
# Unchanged happy paths
expect "파이프라인 돌려줘" "pipeline:pipeline"
expect "오늘 인스타 카드뉴스 만들어줘" "pipeline:content"
expect "리서치 승인" "pipeline:research-approve"

# Inferred automate never auto-runs Cursor; explicit commands still do
is_explicit_automate "/automate 슬랙 알림 스크립트 추가" && record PASS "explicit /automate keeps Cursor" || record FAIL "explicit /automate"
is_explicit_automate "/cursor threads validate 추가" && record PASS "explicit /cursor keeps Cursor" || record FAIL "explicit /cursor"
is_explicit_automate "링크드인 콘텐츠 자동화 흐름 좀 점검해줘" && record FAIL "inferred automate treated as explicit" || record PASS "inferred automate → HANDOFF only"
# /cursor reaches the automate path from both entrypoints
expect "/cursor threads validate 추가" "personal:automate"
expect "/automate 슬랙 알림 스크립트" "personal:automate"

# cursor-handoff.sh auto (commander natural language) must not auto-run Cursor
cursor_auto_value() {
  local tmp; tmp="$(mktemp -d)"
  printf '#!/usr/bin/env bash\necho "HERMES_CURSOR_AUTO=${HERMES_CURSOR_AUTO:-unset}"\n' > "$tmp/telegram-custom.sh"
  chmod +x "$tmp/telegram-custom.sh"
  cp "$DIR/cursor-handoff.sh" "$tmp/"
  (unset HERMES_CURSOR_AUTO; HOME="$tmp" bash "$tmp/cursor-handoff.sh" "$1" "$2" 2>/dev/null | grep -o 'HERMES_CURSOR_AUTO=.*')
  rm -rf "$tmp"
}
[[ "$(cursor_auto_value auto "이 기능 구현해줘")" == "HERMES_CURSOR_AUTO=0" ]] && record PASS "cursor-handoff auto (NL) → HANDOFF only" || record FAIL "cursor-handoff auto (NL) still auto-runs Cursor"
[[ "$(cursor_auto_value auto "/cursor threads validate 추가")" == "HERMES_CURSOR_AUTO=unset" ]] && record PASS "cursor-handoff auto /cursor keeps Cursor" || record FAIL "cursor-handoff auto /cursor"
[[ "$(cursor_auto_value qc "threads validate 추가")" == "HERMES_CURSOR_AUTO=unset" ]] && record PASS "cursor-handoff qc keeps Cursor" || record FAIL "cursor-handoff qc"

echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
