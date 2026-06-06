#!/usr/bin/env bash
# Hermes Content Studio — Telegram 강의 자료 (/lecture)
#
# /pipeline 에서 제외. 자연어 요구사항 → Outline + HTML → Notion
#
# Usage:
#   telegram-lecture.sh "AEO 실전 90분, 대상: B2B 마케터"
#   telegram-lecture.sh qc "프롬프트"     # quick (접수만)
#   telegram-lecture.sh run <job_id>
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
DATE="${DATE:-$(date +%Y-%m-%d)}"
LOG="$HOME/.hermes/logs/content-studio.log"
JOB_DIR="$WORKDIR/.harness/jobs"

mkdir -p "$JOB_DIR" "$WORKDIR/content/lectures"

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

slug_title() {
  echo "$1" | tr ' ' '-' | head -c 40 | sed 's/[^a-zA-Z0-9가-힣-]//g'
}

run_lecture_job() {
  local prompt="$1"
  local title slug content_file design_mode
  title=$(echo "$prompt" | head -c 60)
  slug=$(slug_title "$title")
  [[ -z "$slug" ]] && slug="lecture"
  content_file="$WORKDIR/content/lectures/${DATE}_lecture_request_${slug}.txt"
  design_mode="${LECTURE_DESIGN_MODE:-basic}"

  cat > "$content_file" <<EOF
# 강의 기획 요청 (${DATE})

${prompt}

---
Getdesign.md 디자인 시스템 적용.
출력: outline.md, HTML 덱, PPTX(선택).
EOF

  notify "[██░░░] 강의 자료 생성 중…
${title}"

  local start end elapsed
  start=$(date +%s)

  LECTURE_ARGS=("$title" --content-file "$content_file" --design-mode "$design_mode")
  if [[ "$design_mode" == "claude-design" ]]; then
    LECTURE_ARGS+=(--notion-sync)
  fi

  if SKIP_INIT=1 TELEGRAM_CHAT_ID="$CHAT_ID" "$DIR/run-lecture-slides.sh" "${LECTURE_ARGS[@]}" >>"$LOG" 2>&1; then
    end=$(date +%s)
    elapsed=$(( end - start ))
    local outline html
    outline=$(ls -t "$WORKDIR/content/lectures/${DATE}"_*"${slug}"*outline.md 2>/dev/null | head -1 || \
              ls -t "$WORKDIR/content/lectures/${DATE}"_*outline.md 2>/dev/null | head -1 || true)
    html=$(ls -t "$WORKDIR/content/lectures/${DATE}"_*.html 2>/dev/null | head -1 || true)

    if [[ -n "$CHAT_ID" ]]; then
      TELEGRAM_CHAT_ID="$CHAT_ID" "$DIR/archive-to-notion.sh" "$DATE" --force --telegram-chat "$CHAT_ID" \
        >>"$LOG" 2>&1 || true
    fi

    notify "[█████] 강의 자료 완료 (${elapsed}s)
📑 ${outline:-outline}
🎓 ${html:-html}"

    echo "✅ 강의 완료 (${elapsed}s)"
    echo "📑 ${outline:-—}"
    echo "🎓 ${html:-—}"
  else
    notify "❌ 강의 생성 실패 — 로그: content-studio.log"
    echo "❌ 강의 생성 실패"
    return 1
  fi
}

submit_job() {
  local prompt="$1"
  local job_id="lecture-$(date +%s)-$$"
  local job_file="$JOB_DIR/${job_id}.env"
  printf 'PROMPT=%q\nCHAT_ID=%q\nDATE=%q\n' "$prompt" "$CHAT_ID" "$DATE" > "$job_file"
  notify "[█░░░░] 강의 작업 접수
${prompt:0:200}"
  nohup "$0" run "$job_id" >>"$LOG" 2>&1 &
  echo "✅ 강의 접수: $job_id"
  echo "완료 시 Telegram + Notion (Outline·HTML)"
}

run_job() {
  local job_id="$1"
  local job_file="$JOB_DIR/${job_id}.env"
  [[ -f "$job_file" ]] || { echo "❌ job 없음"; exit 1; }
  # shellcheck source=/dev/null
  source "$job_file"
  export TELEGRAM_CHAT_ID="${CHAT_ID:-}"
  run_lecture_job "${PROMPT:-}"
  rm -f "$job_file"
}

MODE="${1:-help}"
ARG="${2:-}"

case "$MODE" in
  qc)
    if [[ -z "$ARG" ]]; then
      echo "사용법: /lecture-studio <강의 주제·대상·분량·요구사항>"
      echo "예: AEO 실전 90분, 대상 B2B 마케터, FAQ 구조 포함"
      exit 0
    fi
    submit_job "$ARG"
    ;;
  run)
    run_job "$ARG"
    ;;
  help|--help|-h)
    echo "Usage: $0 \"강의 요구사항 (자연어)\""
    echo "Telegram: /lecture-studio <요구사항>"
    ;;
  *)
    submit_job "$MODE ${ARG:+$ARG}"
    ;;
esac
