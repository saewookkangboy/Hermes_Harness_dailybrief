#!/usr/bin/env bash
# Hermes Content Studio — Telegram 결정적 파이프라인 라우터
#
# LLM 없이 run-*.sh 직접 실행 + Telegram 진행 알림 + Notion Permalink
#
# Usage:
#   telegram-pipeline.sh pipeline          # research + content
#   telegram-pipeline.sh research|content|sync|lecture|full
#   telegram-pipeline.sh qc pipeline       # quick command (≤30s; Notion sync-bg)
#   telegram-pipeline.sh qc sync-bg        # background Notion sync
#   telegram-pipeline.sh auto "리서치 해줘"  # keyword routing (에이전트용)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
LOG="$HOME/.hermes/logs/content-studio.log"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
studio_refresh_date

load_chat_id() {
  if [[ -n "${TELEGRAM_CHAT_ID:-}" ]]; then
    echo "$TELEGRAM_CHAT_ID"
    return
  fi
  local env_file="$HOME/.hermes/.env"
  if [[ -f "$env_file" ]]; then
    local v
    v=$(grep -E '^TELEGRAM_CHAT_ID=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -n "$v" ]]; then echo "$v"; return; fi
    v=$(grep -E '^TELEGRAM_ALLOWED_USERS=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -n "$v" ]]; then echo "$v"; return; fi
  fi
  echo ""
}

CHAT_ID="$(load_chat_id)"

# shellcheck source=lib/slack_home.sh
source "$DIR/lib/slack_home.sh"
load_slack_channel() {
  studio_slack_home_channel
}

SLACK_CHANNEL="$(load_slack_channel)"

notify() {
  local msg="$1"
  studio_refresh_date
  local dated="📅 ${DATE}
${msg}"
  [[ -n "$CHAT_ID" ]] && "$DIR/telegram-notify.sh" "$CHAT_ID" "$dated" 2>/dev/null || true
  [[ -n "$SLACK_CHANNEL" ]] && "$DIR/slack-notify.sh" "$SLACK_CHANNEL" "$dated" 2>/dev/null || true
}

detect_personal() {
  local msg="${1:-}"
  local lower
  lower=$(echo "$msg" | tr '[:upper:]' '[:lower:]')
  echo "$lower" | grep -qE \
    '이메일|email|mail|받편지함|inbox|메일|개인|맞춤|custom|자동화|automate|codex|구현|심층|deep.?dive|personal'
}

detect_action() {
  local msg="${1:-}"
  local lower
  lower=$(echo "$msg" | tr '[:upper:]' '[:lower:]')

  if echo "$lower" | grep -qE '노션|notion|동기화|sync|permalink|permalink'; then
    echo "sync"
  elif echo "$lower" | grep -qE '강의|lecture|slide|슬라이드|pptx|claude.?design'; then
    echo "lecture_hint"
  elif echo "$lower" | grep -qE '리서치|research|brief|브리프|트렌드'; then
    echo "research"
  elif echo "$lower" | grep -qE '콘텐츠|content|blog|블로그|instagram|인스타|linkedin|링크드인|소셜'; then
    echo "content"
  elif echo "$lower" | grep -qE '파이프라인|pipeline|전체|주간|weekly|패키지'; then
    echo "pipeline"
  elif echo "$lower" | grep -qE '노션.?상태|notion.?status|아카이브.?점검|중복'; then
    echo "notion-status"
  elif echo "$lower" | grep -qE '상태|status|health|헬스'; then
    echo "status"
  else
    echo "pipeline"
  fi
}

run_research() {
  studio_refresh_date
  local start end elapsed
  start=$(date +%s)
  notify "[██░░░] 2/5 리서치 브리프 생성 중…"
  SKIP_INIT=1 "$DIR/run-research-brief.sh" >>"$LOG" 2>&1
  end=$(date +%s)
  elapsed=$(( end - start ))
  studio_refresh_date
  echo "✅ 리서치 완료 (${elapsed}s)"
  echo "📄 $WORKDIR/content/research/${DATE}_brief.md"
}

run_content() {
  studio_refresh_date
  local start end elapsed
  start=$(date +%s)
  notify "[███░░] 3/5 콘텐츠 패키지 조립 중…"
  SKIP_INIT=1 "$DIR/run-content-package.sh" "$DATE" >>"$LOG" 2>&1
  end=$(date +%s)
  elapsed=$(( end - start ))
  echo "✅ 콘텐츠 완료 (${elapsed}s)"
  ls "$WORKDIR/content/blog/${DATE}"_blog_* 2>/dev/null | head -1 || true
  ls "$WORKDIR/content/instagram/${DATE}"_instagram_* 2>/dev/null | head -1 || true
  ls "$WORKDIR/content/linkedin/${DATE}"_linkedin_* 2>/dev/null | head -1 || true
}

run_pipeline() {
  studio_refresh_date
  notify "[█░░░░] 1/5 파이프라인 시작 ($DATE)"
  local start end elapsed
  start=$(date +%s)
  run_research
  HERMES_SKIP_RESEARCH=1 run_content
  end=$(date +%s)
  elapsed=$(( end - start ))
  notify "[████░] 4/5 콘텐츠 완료 (${elapsed}s) — Notion 강제 동기화"
  echo ""
  echo "=== 파이프라인 완료: ${elapsed}s ==="
  run_sync
}

run_pipeline_qc() {
  studio_refresh_date
  notify "[█░░░░] 1/5 파이프라인 시작 ($DATE)"
  local start end elapsed
  start=$(date +%s)
  run_research
  HERMES_SKIP_RESEARCH=1 run_content
  end=$(date +%s)
  elapsed=$(( end - start ))
  notify "[████░] 4/5 콘텐츠 완료 (${elapsed}s) — Notion 백그라운드 동기화"
  if [[ -n "$SLACK_CHANNEL" ]]; then
    SKIP_INIT=1 "$DIR/slack-daily-log.sh" "$DATE" --build-only 2>>"$LOG" || true
    notify "📋 Daily digest 저장됨 — Notion sync 후 Slack 전송"
  fi
  echo ""
  echo "=== 파이프라인 완료: ${elapsed}s ==="
  run_sync_bg
}

run_sync() {
  studio_refresh_date
  if [[ -z "$CHAT_ID" && -z "$SLACK_CHANNEL" ]]; then
    echo "⚠️ TELEGRAM_CHAT_ID / SLACK_HOME_CHANNEL 없음 — Notion만 동기화"
  fi
  notify "[████░] 4/5 Notion 동기화 중…"
  local start end elapsed
  start=$(date +%s)
  TELEGRAM_CHAT_ID="$CHAT_ID" SLACK_HOME_CHANNEL="$SLACK_CHANNEL" \
    "$DIR/archive-to-notion.sh" "$DATE" --force --notify-final \
    ${CHAT_ID:+--telegram-chat "$CHAT_ID"} \
    ${SLACK_CHANNEL:+--slack-channel "$SLACK_CHANNEL"} >>"$LOG" 2>&1
  end=$(date +%s)
  elapsed=$(( end - start ))
  echo "✅ Notion 동기화 (${elapsed}s) — Telegram/Slack 최종 알림 전송됨"
}

run_sync_bg() {
  studio_refresh_date
  (
    export DATE SLACK_CHANNEL
    TELEGRAM_CHAT_ID="$CHAT_ID" "$0" sync
  ) >>"$LOG" 2>&1 &
  echo "✅ Notion 동기화 시작 (백그라운드)"
  if [[ -n "$SLACK_CHANNEL" && -n "$CHAT_ID" ]]; then
    echo "Permalink는 Telegram + Slack으로 곧 전송됩니다."
  elif [[ -n "$SLACK_CHANNEL" ]]; then
    echo "Permalink는 Slack으로 곧 전송됩니다."
  else
    echo "Permalink는 Telegram으로 곧 전송됩니다."
  fi
}

run_lecture() {
  notify "[███░░] 3/5 강의 슬라이드 생성 중…"
  local start end elapsed
  start=$(date +%s)
  SKIP_INIT=1 "$DIR/run-lecture-slides.sh" --from-brief "$DATE" >>"$LOG" 2>&1
  end=$(date +%s)
  elapsed=$(( end - start ))
  echo "✅ 강의 슬라이드 (${elapsed}s)"
  ls "$WORKDIR/content/lectures/${DATE}"_lecture_* 2>/dev/null | head -3 || true
}

run_full() {
  run_pipeline
  run_sync
}

run_notion_status() {
  studio_refresh_date
  local fix="${1:-}"
  notify "[██░░░] Notion 아카이브 점검 중…"
  if [[ "$fix" == "--fix" ]]; then
    "$DIR/check-notion-status.sh" "$DATE" --fix
  else
    "$DIR/check-notion-status.sh" "$DATE"
  fi
}

run_status() {
  studio_refresh_date
  echo "=== Hermes Content Studio ==="
  echo "날짜: $DATE"
  echo "워크디렉: $WORKDIR"
  [[ -f "$WORKDIR/content/research/${DATE}_brief.md" ]] && echo "✅ brief" || echo "⬜ brief"
  ls "$WORKDIR/content/blog/${DATE}"_blog_* >/dev/null 2>&1 && echo "✅ blog" || echo "⬜ blog"
  ls "$WORKDIR/content/instagram/${DATE}"_instagram_* >/dev/null 2>&1 && echo "✅ instagram" || echo "⬜ instagram"
  ls "$WORKDIR/content/linkedin/${DATE}"_linkedin_* >/dev/null 2>&1 && echo "✅ linkedin" || echo "⬜ linkedin"
  pgrep -f "hermes_cli.main gateway" >/dev/null && echo "✅ Gateway" || echo "❌ Gateway"
  echo ""
  echo "명령: /pipeline /research /content /sync /studio /notion-status (Telegram·Slack)"
  echo "개인화: /mail /personal /automate"
  echo "강의: /lecture-studio <요구사항>"
}

MODE="${1:-pipeline}"
ACTION="${2:-}"

case "$MODE" in
  qc)
    # Quick command — Hermes 30s timeout 준수
    case "$ACTION" in
      pipeline)
        run_pipeline_qc
        ;;
      research)
        notify "[█░░░░] 1/5 리서치 시작"
        run_research
        ;;
      content)
        notify "[█░░░░] 1/5 콘텐츠 시작"
        run_content
        ;;
      sync-bg)
        run_sync_bg
        ;;
      sync|sync-now)
        run_sync
        ;;
      pipeline-sync)
        run_sync
        ;;
      status|studio)
        run_status
        ;;
      notion-status|notion_status)
        run_notion_status
        ;;
      notion-fix)
        run_notion_status --fix
        ;;
      *)
        echo "Unknown qc action: $ACTION"
        exit 1
        ;;
    esac
    ;;
  auto)
    MSG="${ACTION:-}"
    if detect_personal "$MSG"; then
      exec "$DIR/telegram-custom.sh" auto "$MSG"
    fi
    DETECTED=$(detect_action "$MSG")
    if [[ "$DETECTED" == "lecture_hint" ]]; then
      echo "ℹ️ 강의 자료는 /pipeline이 아닌 /lecture 명령을 사용하세요."
      echo "예: /lecture-studio AEO 실전 90분, 대상 B2B 마케터"
      exit 0
    fi
    echo "# 라우팅: $DETECTED ← \"$MSG\""
    case "$DETECTED" in
      research) run_research ;;
      content)  run_content ;;
      pipeline) run_pipeline ;;
      sync)     run_sync ;;
      status)   run_status ;;
      notion-status) run_notion_status ;;
      lecture_hint)
        echo "강의: /lecture-studio 명령 사용"
        ;;
      *)        run_pipeline ;;
    esac
    ;;
  research)  notify "[█░░░░] 1/5"; run_research ;;
  content)   notify "[█░░░░] 1/5"; run_content ;;
  pipeline)  run_pipeline ;;
  sync)      run_sync ;;
  sync-bg)   run_sync_bg ;;
  status|studio) run_status ;;
  *)
    echo "Usage: $0 {pipeline|research|content|sync|lecture|full|status|qc|auto} [args]"
    exit 1
    ;;
esac
