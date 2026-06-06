#!/usr/bin/env bash
# Hermes Content Studio — Telegram 개인화·커스텀 작업
#
# /pipeline 과 별도: 맞춤 리서치, 이메일 정리, Codex 자동화
#
# Usage:
#   telegram-custom.sh qc mail              # 이메일 다이제스트 (백그라운드)
#   telegram-custom.sh qc ask-bg "프롬프트"   # 개인화 작업 (백그라운드)
#   telegram-custom.sh auto "이메일 확인"     # 키워드 라우팅
#   telegram-custom.sh run <job_id>         # 내부: 작업 실행
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
DATE="${DATE:-$(date +%Y-%m-%d)}"
LOG="$HOME/.hermes/logs/content-studio.log"
JOB_DIR="$WORKDIR/.harness/jobs"
OUT_DIR="$WORKDIR/content/personal"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

mkdir -p "$JOB_DIR" "$OUT_DIR"

# shellcheck source=lib/hermes-codex.sh
source "$DIR/lib/hermes-codex.sh"

load_chat_id() {
  if [[ -n "${TELEGRAM_CHAT_ID:-}" ]]; then
    echo "$TELEGRAM_CHAT_ID"
    return
  fi
  local env_file="$HOME/.hermes/.env"
  if [[ -f "$env_file" ]]; then
    local v
    v=$(grep -E '^TELEGRAM_CHAT_ID=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    [[ -n "$v" ]] && { echo "$v"; return; }
    v=$(grep -E '^TELEGRAM_ALLOWED_USERS=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    [[ -n "$v" ]] && { echo "$v"; return; }
  fi
  echo ""
}

CHAT_ID="$(load_chat_id)"

notify() {
  local msg="$1"
  [[ -z "$CHAT_ID" ]] && return 0
  "$DIR/telegram-notify.sh" "$CHAT_ID" "$msg" 2>/dev/null || true
}

slug_from_prompt() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9가-힣]\+/ /g' | awk '{print $1"-"$2}' | head -c 30 | sed 's/-$//'
}

detect_task_type() {
  local msg="${1:-}"
  local lower
  lower=$(echo "$msg" | tr '[:upper:]' '[:lower:]')

  if echo "$lower" | grep -qE '이메일|email|mail|받편지함|inbox|메일함'; then
    echo "mail"
  elif echo "$lower" | grep -qE '자동화|automate|automation|codex|스크립트|구현|코드'; then
    echo "automate"
  elif echo "$lower" | grep -qE '리서치|research|조사|분석|트렌드|survey|deep.?dive'; then
    echo "research"
  else
    echo "ask"
  fi
}

run_mail_digest() {
  notify "[██░░░] 이메일 확인 중…"
  local out backend="mailapp"
  if command -v himalaya >/dev/null 2>&1; then backend="himalaya"; fi
  if [[ -x "$HERMES_PY" ]]; then
    out=$("$HERMES_PY" "$DIR/mail-digest.py" --backend "$backend" --max 15 2>>"$LOG")
  else
    out=$(python3 "$DIR/mail-digest.py" --backend "$backend" --max 15 2>>"$LOG")
  fi
  local digest_file
  digest_file=$(echo "$out" | head -1)
  echo "✅ 이메일 다이제스트 완료"
  echo "📄 $digest_file"
  notify "[█████] 이메일 정리 완료
📄 $digest_file
/personal 로 Codex 심화 분석 가능"
}

run_hermes_codex() {
  local task_type="$1"
  local prompt="$2"
  local slug skills toolsets
  slug=$(slug_from_prompt "$prompt")
  [[ -z "$slug" || "$slug" == "-" ]] && slug="task"

  local out_file="$OUT_DIR/${DATE}_${task_type}_${slug}.md"
  local skills="personal-assistant"
  toolsets="${HERMES_TOOLSETS:-hermes-cli}"

  case "$task_type" in
    automate)
      skills="personal-assistant,vibe-coding-cursor"
      toolsets="hermes-cli"
      local handoff_base="$WORKDIR/content/drafts/cursor-handoff/${DATE}_${slug}"
      export HERMES_CURSOR_HANDOFF="${handoff_base}_HANDOFF.md"
      ;;
    research)
      skills="personal-assistant,marketing-research"
      toolsets="hermes-cli"
      ;;
  esac

  notify "[██░░░] ${task_type} 작업 (Codex)…"

  local full_prompt
  full_prompt="[Telegram 개인화 · ${task_type}]
${prompt}

필수:
- 산출물: ${out_file}
- 한국어, 실무형 톤
- 완료 시 파일 경로와 3줄 요약"

  if [[ "$task_type" == "automate" && -n "${HERMES_CURSOR_HANDOFF:-}" ]]; then
    full_prompt="${full_prompt}
- vibe-coding-cursor: ${HERMES_CURSOR_HANDOFF} (+ _CONTEXT.md, _TASKS.md)
- HANDOFF에 **대상 레포:** 절대경로 필수"
  fi

  export HERMES_USE_CODEX=1
  export HERMES_WORKDIR="$WORKDIR"

  local start end elapsed
  start=$(date +%s)

  HERMES_USE_CODEX=1 HERMES_TOOLSETS="$toolsets" "$DIR/hermes-run.sh" "$full_prompt" --skills "$skills" \
    > "${out_file}.reply" 2>>"$LOG" || true

  end=$(date +%s)
  elapsed=$(( end - start ))

  {
    echo "# 개인화 작업 — ${task_type}"
    echo "**일시:** $(date '+%Y-%m-%d %H:%M')"
    echo "**요청:** ${prompt}"
    echo ""
    echo "## 응답"
    cat "${out_file}.reply" 2>/dev/null || echo "(응답 없음)"
  } > "$out_file"
  rm -f "${out_file}.reply"

  echo "✅ ${task_type} 완료 (${elapsed}s)"
  echo "📄 $out_file"
  notify "[█████] ${task_type} 완료 (${elapsed}s)
📄 ${out_file}"

  if [[ "$task_type" == "automate" && "${HERMES_CURSOR_AUTO:-1}" != "0" ]]; then
    local handoff_arg=()
    if [[ -n "${HERMES_CURSOR_HANDOFF:-}" && -f "${HERMES_CURSOR_HANDOFF}" ]]; then
      handoff_arg=(--handoff "${HERMES_CURSOR_HANDOFF}")
    else
      handoff_arg=(--latest)
    fi
    if ls "$WORKDIR/content/drafts/cursor-handoff/"*_HANDOFF.md >/dev/null 2>&1; then
      notify "[█░░░░] Cursor CLI 자동 실행…"
      "$DIR/run-cursor-handoff.sh" --background "${handoff_arg[@]}" || \
        notify "⚠️ Cursor CLI 실행 실패 — ./scripts/install-cursor-cli.sh"
    else
      notify "ℹ️ HANDOFF 없음 — Cursor CLI 생략 (vibe-coding-cursor 산출물 확인)"
    fi
  fi
}

submit_job() {
  local task_type="$1"
  local prompt="${2:-}"
  local job_id="job-$(date +%s)-$$"
  local job_file="$JOB_DIR/${job_id}.env"

  cat > "$job_file" <<EOF
TASK_TYPE=$task_type
PROMPT=$(printf '%q' "$prompt")
CHAT_ID=$CHAT_ID
DATE=$DATE
EOF

  notify "[█░░░░] 개인화 작업 접수 ($task_type)
${prompt:0:200}"

  nohup "$0" run "$job_id" >>"$LOG" 2>&1 &
  echo "✅ 작업 접수: $job_id ($task_type)"
  echo "완료 시 Telegram 알림 · 로그: $LOG"
}

run_job() {
  local job_id="$1"
  local job_file="$JOB_DIR/${job_id}.env"
  [[ -f "$job_file" ]] || { echo "❌ job 없음: $job_id"; exit 1; }

  # shellcheck source=/dev/null
  source "$job_file"
  CHAT_ID="${CHAT_ID:-}"
  export TELEGRAM_CHAT_ID="$CHAT_ID"
  DATE="${DATE:-$(date +%Y-%m-%d)}"

  case "${TASK_TYPE:-ask}" in
    mail)
      run_mail_digest
      # 선택: Codex 후처리
      if [[ -n "${PROMPT:-}" ]] && echo "$PROMPT" | grep -qE '요약|정리|액션|분석'; then
        run_hermes_codex "ask" "다음 이메일 다이제스트를 바탕으로 액션 아이템과 우선순위를 정리: ${PROMPT}"
      fi
      ;;
    *)
      run_hermes_codex "${TASK_TYPE:-ask}" "${PROMPT:-}"
      ;;
  esac

  rm -f "$job_file"
}

run_status() {
  echo "=== 개인화 작업 (Personal) ==="
  echo "출력: $OUT_DIR"
  ls -lt "$OUT_DIR" 2>/dev/null | head -6 || echo "(산출물 없음)"
  echo ""
  echo "명령:"
  echo "  /mail              이메일 확인·정리"
  echo "  /personal <요청>   맞춤 리서치·Codex 작업"
  echo "  /automate <설명>   자동화 구현 (Codex)"
  echo ""
  if hermes auth status openai-codex 2>&1 | grep -q "logged in"; then
    echo "✅ Codex 연결됨"
  else
    echo "⚠️  Codex 미연결 — ./scripts/setup-codex.sh"
  fi
}

MODE="${1:-status}"
ARG="${2:-}"

case "$MODE" in
  qc)
    case "$ARG" in
      mail)
        submit_job mail "받편함 확인 및 요약"
        ;;
      ask-bg)
        submit_job "$(detect_task_type "${3:-}")" "${3:-}"
        ;;
      status)
        run_status
        ;;
      *)
        echo "Unknown qc: $ARG"
        exit 1
        ;;
    esac
    ;;
  auto)
    TYPE=$(detect_task_type "$ARG")
    echo "# 개인화: $TYPE ← \"$ARG\""
    submit_job "$TYPE" "$ARG"
    ;;
  mail)
    submit_job mail "${ARG:-받편함 확인}"
    ;;
  research|automate|ask)
    submit_job "$MODE" "$ARG"
    ;;
  run)
    run_job "$ARG"
    ;;
  status)
    run_status
    ;;
  *)
    echo "Usage: $0 {mail|research|automate|ask|auto|run|qc|status} [args]"
    exit 1
    ;;
esac
