#!/usr/bin/env bash
# Hermes Content Studio — 상태 표시바와 함께 Hermes 작업 실행
#
# Usage:
#   ./hermes-run.sh "프롬프트" --skills skill1,skill2
#   ./hermes-run.sh "리서치 브리프 작성" --skills marketing-research
#   HERMES_TOOLSETS=hermes-cli ./hermes-run.sh "..." --skills marketing-research
#
# -z 대신 chat -q + verbose 로 진행 상황 표시
# stderr 에 상태바, stdout 에 최종 응답
set -euo pipefail

PROMPT="${1:?Usage: hermes-run.sh \"prompt\" [--skills name] [-t toolsets]}"
shift

SKILLS=""
TOOLSETS="${HERMES_TOOLSETS:-}"
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skills|-s)
      SKILLS="$2"
      shift 2
      ;;
    -t|--toolsets)
      TOOLSETS="$2"
      shift 2
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

# 콘텐츠 생성 시 MCP·브라우저 제외 → 로컬 모델 truncation 완화
if [[ -z "$TOOLSETS" ]]; then
  case "$SKILLS" in
    marketing-research|content-pipeline|content-studio-slides|claude-design*)
      TOOLSETS="hermes-cli"
      ;;
    personal-assistant|personal|*personal*)
      TOOLSETS="hermes-cli"
      ;;
    *claude-design*)
      TOOLSETS="hermes-cli"
      ;;
  esac
fi

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
SCRIPTS="$WORKDIR/scripts"
# shellcheck source=lib/hermes-codex.sh
source "$SCRIPTS/lib/hermes-codex.sh"
LOG_FILE="${HERMES_RUN_LOG:-/tmp/hermes-run-$$.log}"
BAR_WIDTH=24
USE_CODEX=0
if hermes_should_use_codex "$SKILLS"; then
  USE_CODEX=1
fi
MODEL_LABEL=$(hermes_codex_status_label "$SKILLS")

# ── 상태바 유틸 ─────────────────────────────────────────────
render_bar() {
  local elapsed="$1"
  local phase="$2"
  local ollama_cpu="${3:-0}"
  local filled=$(( elapsed % (BAR_WIDTH + 1) ))
  local bar=""
  local i
  for ((i=0; i<BAR_WIDTH; i++)); do
    if (( i < filled )); then bar+="█"; else bar+="░"; fi
  done
  local mins=$(( elapsed / 60 ))
  local secs=$(( elapsed % 60 ))
  printf '\r\033[K[%s] %02d:%02d | %s | %s %s%%' "$bar" "$mins" "$secs" "$phase" "$MODEL_LABEL" "$ollama_cpu" >&2
}

detect_phase() {
  if [[ ! -s "$LOG_FILE" ]]; then
    echo "시작 중"
    return
  fi
  local tail3
  tail3=$(tail -3 "$LOG_FILE" 2>/dev/null)
  if echo "$tail3" | grep -qiE "web_search|ddgs|search"; then
    echo "웹 검색"
  elif echo "$tail3" | grep -qiE "write_file|patch"; then
    echo "파일 저장"
  elif echo "$tail3" | grep -qiE "terminal|Tool:"; then
    echo "도구 실행"
  elif pgrep -f "llama-server" >/dev/null 2>&1; then
    local cpu
    cpu=$(get_ollama_cpu)
    if [[ -n "$cpu" && "$cpu" -gt 5 ]]; then
      echo "LLM 추론"
    else
      echo "대기/처리"
    fi
  else
    echo "시작 중"
  fi
}

get_ollama_cpu() {
  ps aux 2>/dev/null | rg "llama-server" | rg -v rg | awk '{print int($3)}' | head -1 || echo "0"
}

# ── Hermes 실행 ─────────────────────────────────────────────
CMD=(hermes chat -q "$PROMPT" -v)
if [[ "$USE_CODEX" == "1" ]]; then
  # Codex 구독 OAuth — claude-design·HERMES_ENHANCE 품질 경로
  CMD+=(--provider "$HERMES_CODEX_PROVIDER" -m "$HERMES_CODEX_MODEL")
fi
if [[ -n "$SKILLS" ]]; then
  CMD+=(-s "$SKILLS")
fi
if [[ -n "$TOOLSETS" ]]; then
  CMD+=(-t "$TOOLSETS")
fi
if ((${#EXTRA_ARGS[@]} > 0)); then
  CMD+=("${EXTRA_ARGS[@]}")
fi

echo "=== Hermes 실행 ===" >&2
echo "프롬프트: $PROMPT" >&2
echo "스킬: ${SKILLS:-없음}" >&2
echo "모델: ${MODEL_LABEL} (${HERMES_CODEX_MODEL:-gemma4:latest})" >&2
echo "도구: ${TOOLSETS:-전체}" >&2
echo "워크디렉: $WORKDIR" >&2
echo "로그: $LOG_FILE" >&2
echo "" >&2

cd "$WORKDIR"
: > "$LOG_FILE"

"${CMD[@]}" > "$LOG_FILE" 2>&1 &
HERMES_PID=$!

START=$(date +%s)
while kill -0 "$HERMES_PID" 2>/dev/null; do
  NOW=$(date +%s)
  ELAPSED=$(( NOW - START ))
  PHASE=$(detect_phase)
  CPU=$(get_ollama_cpu)
  render_bar "$ELAPSED" "$PHASE" "$CPU"
  sleep 2
done

wait "$HERMES_PID" || EXIT=$?
EXIT=${EXIT:-0}

echo "" >&2
echo "=== 완료 (exit: $EXIT) ===" >&2

# stdout: verbose 로그에서 최종 응답만 추출 (가능한 경우)
if rg -q "^Assistant:" "$LOG_FILE" 2>/dev/null; then
  rg "^Assistant:" "$LOG_FILE" | tail -1 | sed 's/^Assistant: //'
elif rg -q "write_file|Successfully" "$LOG_FILE" 2>/dev/null; then
  tail -20 "$LOG_FILE" | rg -v "^(Tool:|Using |Searching|\[)" || tail -5 "$LOG_FILE"
else
  tail -30 "$LOG_FILE"
fi

# 산출물 검증 힌트
BRIEF=$(ls -t "$WORKDIR/content/research/"*_brief.md 2>/dev/null | grep -v SEED | head -1 || true)
if [[ -n "$BRIEF" ]]; then
  echo "" >&2
  echo "📄 research: $BRIEF" >&2
fi
for dir in blog instagram linkedin lectures; do
  LATEST=$(ls -t "$WORKDIR/content/$dir/"* 2>/dev/null | head -1 || true)
  if [[ -n "$LATEST" ]]; then
    echo "📄 $dir: $LATEST" >&2
  fi
done

exit "$EXIT"
