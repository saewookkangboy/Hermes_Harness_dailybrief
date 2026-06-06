#!/usr/bin/env bash
# Hermes Content Studio — Cursor Agent CLI 자동 실행 (HANDOFF.md)
#
# Usage:
#   run-cursor-handoff.sh --latest                    # 최신 HANDOFF 실행
#   run-cursor-handoff.sh --handoff PATH [--cwd DIR]  # 지정 HANDOFF
#   run-cursor-handoff.sh --dry-run --latest          # 명령만 출력
#   run-cursor-handoff.sh --background --latest       # 백그라운드 + Telegram 알림
#
# 환경:
#   HERMES_CURSOR_AUTO=1     telegram-custom automate 후 자동 호출 (기본)
#   CURSOR_API_KEY           cursor-agent 인증 (없으면 로컬 세션)
#   HERMES_WORKDIR           스튜디오 루트
#
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HANDOFF_DIR="$WORKDIR/content/drafts/cursor-handoff"
LOG="${HERMES_CURSOR_LOG:-$HOME/.hermes/logs/cursor-handoff.log}"
DATE="${DATE:-$(date +%Y-%m-%d)}"

# shellcheck source=lib/cursor-cli.sh
source "$DIR/lib/cursor-cli.sh"

HANDOFF=""
CWD=""
DRY_RUN=0
BACKGROUND=0
USE_LATEST=0
MODEL="${CURSOR_AGENT_MODEL:-}"
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Usage: run-cursor-handoff.sh [options]

Options:
  --latest              handoff_dir에서 최신 *_HANDOFF.md 사용
  --handoff PATH        HANDOFF.md 경로
  --cwd PATH            워크스페이스 (HANDOFF 미지정 시 대상 레포에서 추출)
  --model MODEL         cursor-agent --model (예: composer-2.5)
  --dry-run             실행하지 않고 명령·경로만 출력
  --background          nohup 백그라운드 실행 + Telegram 알림
  --force               --force --trust (기본: headless 자동화 시 활성)
  -h, --help            도움말

Examples:
  run-cursor-handoff.sh --latest
  run-cursor-handoff.sh --handoff content/drafts/cursor-handoff/2026-06-06_foo_HANDOFF.md
  run-cursor-handoff.sh --dry-run --latest
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --latest) USE_LATEST=1; shift ;;
    --handoff) HANDOFF="$2"; shift 2 ;;
    --cwd) CWD="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --background) BACKGROUND=1; shift ;;
    --force) EXTRA_ARGS+=(--force --trust); shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

mkdir -p "$(dirname "$LOG")" "$HANDOFF_DIR"

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

notify() {
  local msg="$1"
  local chat_id
  chat_id=$(load_chat_id)
  [[ -z "$chat_id" ]] && return 0
  "$DIR/telegram-notify.sh" "$chat_id" "$msg" 2>/dev/null || true
}

find_latest_handoff() {
  local latest
  latest=$(ls -t "$HANDOFF_DIR"/*_HANDOFF.md 2>/dev/null | head -1 || true)
  if [[ -z "$latest" ]]; then
    echo "❌ HANDOFF 없음: $HANDOFF_DIR/*_HANDOFF.md" >&2
    echo "  Hermes /automate 또는 vibe-coding-cursor 스킬로 생성 후 재시도" >&2
    exit 1
  fi
  echo "$latest"
}

parse_repo_from_handoff() {
  local file="$1"
  local repo=""
  repo=$(grep -E '^\*\*대상 레포:\*\*|^\*\*대상 레포\*\*' "$file" 2>/dev/null | head -1 \
    | sed -E 's/^\*\*대상 레포:?\*\*[[:space:]]*//' \
    | sed -E 's/^[` ]+|[` ]+$//g' || true)
  if [[ -z "$repo" ]]; then
    repo=$(grep -E '^- \*\*대상 레포\*\*:|^대상 레포:' "$file" 2>/dev/null | head -1 \
      | sed -E 's/^[-*[:space:]]*(\*\*)?대상 레포(\*\*)?:[[:space:]]*//' \
      | sed -E 's/^[` ]+|[` ]+$//g' || true)
  fi
  if [[ -z "$repo" || ! -d "$repo" ]]; then
    echo "❌ HANDOFF에서 유효한 대상 레포를 찾을 수 없음: $file" >&2
    echo "  HANDOFF.md에 **대상 레포:** /absolute/path 형식 필요" >&2
    exit 1
  fi
  echo "$repo"
}

build_prompt() {
  local handoff_file="$1"
  cat <<EOF
Hermes Content Studio Cursor Handoff — 자동 실행

다음 HANDOFF 문서 내용을 정확히 따라 구현하세요.
범위 최소화, 기존 컨벤션(AGENTS.md/CLAUDE.md) 준수, 완료 후 빌드/테스트 명령 실행.

--- HANDOFF START ---
$(cat "$handoff_file")
--- HANDOFF END ---
EOF
}

resolve_handoff() {
  if [[ "$USE_LATEST" == "1" && -z "$HANDOFF" ]]; then
    HANDOFF=$(find_latest_handoff)
  fi
  if [[ -z "$HANDOFF" ]]; then
    echo "❌ --latest 또는 --handoff PATH 필요" >&2
    usage >&2
    exit 1
  fi
  if [[ ! -f "$HANDOFF" ]]; then
    echo "❌ HANDOFF 파일 없음: $HANDOFF" >&2
    exit 1
  fi
  if [[ -z "$CWD" ]]; then
    CWD=$(parse_repo_from_handoff "$HANDOFF")
  fi
  if [[ ! -d "$CWD" ]]; then
    echo "❌ 워크스페이스 없음: $CWD" >&2
    exit 1
  fi
}

run_agent() {
  local agent handoff_file workspace prompt
  handoff_file="$1"
  workspace="$2"

  if ! agent=$(cursor_cli_resolve_agent); then
    echo "❌ cursor-agent 미설치 — ./scripts/install-cursor-cli.sh" >&2
    exit 1
  fi

  if [[ "$DRY_RUN" != "1" ]] && [[ -z "${CURSOR_API_KEY:-}" ]] && ! cursor_cli_auth_ready 2>/dev/null; then
    echo "❌ cursor-agent 인증 필요" >&2
    echo "  cursor-agent login   # 브라우저 OAuth (1회, headless 자동화 필수)" >&2
    echo "  또는 ~/.hermes/.env 에 CURSOR_API_KEY 설정" >&2
    notify "⚠️ Cursor Agent 인증 필요 — 터미널에서 cursor-agent login 실행"
    exit 1
  fi

  prompt=$(build_prompt "$handoff_file")

  local -a cmd
  cmd=("$agent" --print --trust --force --approve-mcps --workspace "$workspace")
  if [[ -n "$MODEL" ]]; then
    cmd+=(--model "$MODEL")
  fi
  if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
    cmd+=("${EXTRA_ARGS[@]}")
  fi
  cmd+=("$prompt")

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "=== dry-run ==="
    echo "handoff: $handoff_file"
    echo "workspace: $workspace"
    echo "agent: $agent"
    echo "log: $LOG"
    echo ""
    echo "command:"
    printf ' %q' "${cmd[@]}"
    echo ""
    echo ""
    echo "prompt (first 500 chars):"
    echo "$prompt" | head -c 500
    echo "..."
    return 0
  fi

  {
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') cursor-handoff ==="
    echo "handoff: $handoff_file"
    echo "workspace: $workspace"
    echo "agent: $agent"
    echo "---"
  } >>"$LOG"

  notify "[██░░░] Cursor Agent 실행 중…
📄 $(basename "$handoff_file")
📁 $workspace"

  if [[ "$BACKGROUND" == "1" ]]; then
    nohup "${cmd[@]}" >>"$LOG" 2>&1 &
    local pid=$!
    echo "✅ Cursor Agent 백그라운드 시작 (pid=$pid)"
    echo "📄 handoff: $handoff_file"
    echo "📁 workspace: $workspace"
    echo "📋 log: $LOG"
    notify "[███░░] Cursor Agent 백그라운드 (pid=$pid)
📋 $LOG"
    return 0
  fi

  local start end elapsed
  start=$(date +%s)
  "${cmd[@]}" 2>&1 | tee -a "$LOG"
  end=$(date +%s)
  elapsed=$(( end - start ))

  echo ""
  echo "✅ Cursor Agent 완료 (${elapsed}s)"
  echo "📋 log: $LOG"
  notify "[█████] Cursor Agent 완료 (${elapsed}s)
📋 $LOG"
}

resolve_handoff
run_agent "$HANDOFF" "$CWD"
