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
# shellcheck source=lib/telegram_sync_guard.sh
source "$DIR/lib/telegram_sync_guard.sh"
studio_refresh_date
DATE="$(studio_commander_date)"
export DATE

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
  DATE="$(studio_commander_date)"
  export DATE
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

detect_intent_pack() {
  local msg="${1:-}"
  if "$DIR/hermes-agent.sh" auto "$msg" --date "$DATE" 2>/dev/null; then
    return 0
  fi
  return 1
}

detect_action() {
  local msg="${1:-}"
  local lower
  lower=$(echo "$msg" | tr '[:upper:]' '[:lower:]')

  if echo "$lower" | grep -qE '리서치.?승인|/research-approve|research-approve'; then
    echo "research-approve"
    return
  fi
  if echo "$lower" | grep -qE '리서치.?대기|/research-pending|research-pending'; then
    echo "research-pending"
    return
  fi

  if echo "$lower" | grep -qE '^/(morning|catch-up|catchup|publish|approve|deep|ask|linkedin|blog|instagram|audit|repurpose|schedule|schedules|supervised|wiki|squad|watch|coach|agents-eval|agents|traces|handoff|graph|commands|newsletter)\b'; then
    echo "intent-pack"
    return
  fi
  if echo "$lower" | grep -qE '^(모닝|아침 브리핑|최근 요약|catch.?up|링크드인 전략|핸드오프|성능 리포트|성과 코치|브리프 그래프|승인|명령 목록|뉴스레터|감독|스케줄|예약|에이전트 검증)'; then
    echo "intent-pack"
    return
  fi

  if echo "$lower" | grep -qE 'agents.?eval|에이전트 검증|agent eval'; then
    echo "agents-eval"
  elif echo "$lower" | grep -qE '노션|notion|동기화|sync|permalink|permalink'; then
    echo "sync"
  elif echo "$lower" | grep -qE '강의|lecture|slide|슬라이드|pptx|claude.?design'; then
    echo "lecture_hint"
  elif echo "$lower" | grep -qE '리서치|research|brief|브리프|트렌드|키워드'; then
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

# Parse natural-language / slash research message → args for run_research_keyword
parse_research_args() {
  local msg="${1:-}"
  local args=()
  echo "$msg" | grep -qiE '(--replace|교체)' && args+=(--replace)
  echo "$msg" | grep -qiE '(--approve|승인 후|스테이징)' && args+=(--approve)
  # Strip command verbs / flags; keep keyword phrase
  local kw
  kw=$(echo "$msg" | sed -E \
    -e 's/^[[:space:]]*\/research[[:space:]]*//I' \
    -e 's/^[[:space:]]*(키워드[[:space:]]*)?리서치[[:space:]]*(해줘|해주세요|부탁)?[[:space:]]*[:：]?[[:space:]]*//I' \
    -e 's/^[[:space:]]*research[[:space:]]*//I' \
    -e 's/--replace//Ig' \
    -e 's/--approve//Ig' \
    -e 's/교체로?//g' \
    -e 's/승인 후(에)?( 반영)?//g' \
    -e 's/스테이징//g' \
    -e 's/키워드[[:space:]]*리서치[[:space:]]*//g')
  kw=$(echo "$kw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  if [[ -n "$kw" ]]; then
    args+=("$kw")
  fi
  printf '%s\n' "${args[@]}"
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

# Keyword research: args after "research" or env HERMES_RESEARCH_*
# Usage: run_research_keyword "RAG 평가" [--replace] [--approve]
run_research_keyword() {
  studio_refresh_date
  local keywords="" replace=0 approve=0 token
  for token in "$@"; do
    case "$token" in
      --replace) replace=1 ;;
      --approve) approve=1 ;;
      *)
        if [[ -n "$keywords" ]]; then
          keywords="$keywords $token"
        else
          keywords="$token"
        fi
        ;;
    esac
  done
  keywords="$(echo "$keywords" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  if [[ -z "$keywords" ]]; then
    run_research
    return
  fi
  notify "[██░░░] 키워드 리서치: $keywords"
  local start end elapsed
  start=$(date +%s)
  HERMES_RESEARCH_KEYWORDS="$keywords" \
  HERMES_RESEARCH_REPLACE="$replace" \
  HERMES_RESEARCH_APPROVE="$approve" \
  HERMES_RESEARCH_FORCE="${HERMES_RESEARCH_FORCE:-1}" \
    SKIP_INIT=1 "$DIR/run-research-brief.sh" >>"$LOG" 2>&1
  end=$(date +%s)
  elapsed=$(( end - start ))
  if [[ "$approve" == "1" ]]; then
    echo "✅ 키워드 리서치 staging (${elapsed}s) — /research-pending · /research-approve"
  elif [[ "$replace" == "1" ]] && python3 -c "import sys; sys.path.insert(0,'$DIR'); from lib.research_merge import require_approve_on_replace; raise SystemExit(0 if require_approve_on_replace() else 1)"; then
    echo "✅ 키워드 replace staging (${elapsed}s) — /research-pending · /research-approve"
  else
    echo "✅ 키워드 반영 완료 (${elapsed}s) — 다운스트림 재실행"
    HERMES_SKIP_RESEARCH=1 run_content
    if [[ "${SKIP_NEWSLETTER:-0}" != "1" ]]; then
      run_newsletter
    fi
  fi
  echo "📄 $WORKDIR/content/research/${DATE}_brief.md"
}

run_research_pending() {
  python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "hermes-content-studio" / "scripts"))
from lib.research_staging import format_pending_status
print(format_pending_status())
PY
}

run_research_approve() {
  studio_refresh_date
  local target="${1:-}"
  HERMES_RESEARCH_APPROVE_TARGET="$target" python3 - <<'PY'
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "hermes-content-studio" / "scripts"))
from lib.research_staging import approve
target = (os.environ.get("HERMES_RESEARCH_APPROVE_TARGET") or "").strip()
if target == "all":
    paths = approve(all_pending=True)
elif target:
    paths = approve(run_id=target)
else:
    paths = approve(all_pending=False)  # first pending
if not paths:
    print("research staging: nothing to approve")
    sys.exit(0)
for p in paths:
    print(f"committed: {p}")
PY
  if ls "$WORKDIR/content/research/${DATE}_brief.md" >/dev/null 2>&1; then
    SKIP_INIT=1 "$DIR/validate-output.sh" research "$WORKDIR/content/research/${DATE}_brief.md" || true
    HERMES_SKIP_RESEARCH=1 run_content
    if [[ "${SKIP_NEWSLETTER:-0}" != "1" ]]; then
      run_newsletter
    fi
  fi
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

run_newsletter() {
  studio_refresh_date
  local start end elapsed
  start=$(date +%s)
  notify "[███░░] 3b/5 B2B 뉴스레터 생성 중…"
  SKIP_INIT=1 "$DIR/run-newsletter.sh" "$DATE" --validate >>"$LOG" 2>&1
  end=$(date +%s)
  elapsed=$(( end - start ))
  echo "✅ 뉴스레터 완료 (${elapsed}s)"
  ls "$WORKDIR/content/newsletter/${DATE}"_newsletter_*.md 2>/dev/null | head -1 || true
  ls "$WORKDIR/content/newsletter/${DATE}"_newsletter_*.html 2>/dev/null | head -1 || true
}

run_pipeline() {
  studio_refresh_date
  notify "[█░░░░] 1/5 파이프라인 시작 ($DATE)"
  local start end elapsed
  start=$(date +%s)
  run_research
  HERMES_SKIP_RESEARCH=1 run_content
  if [[ "${SKIP_NEWSLETTER:-0}" != "1" ]]; then
    run_newsletter
  fi
  end=$(date +%s)
  elapsed=$(( end - start ))
  notify "[████░] 4/5 콘텐츠+뉴스레터 완료 (${elapsed}s) — Notion 강제 동기화"
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
  if [[ "${SKIP_NEWSLETTER:-0}" != "1" ]]; then
    run_newsletter
  fi
  end=$(date +%s)
  elapsed=$(( end - start ))
  notify "[████░] 4/5 콘텐츠+뉴스레터 완료 (${elapsed}s) — Notion 백그라운드 동기화"
  if [[ -n "$SLACK_CHANNEL" ]]; then
    SKIP_INIT=1 "$DIR/slack-daily-log.sh" "$DATE" --build-only 2>>"$LOG" || true
    notify "📋 Daily digest 저장됨 — Notion sync 후 Slack 전송"
  fi
  echo ""
  echo "=== 파이프라인 완료: ${elapsed}s ==="
  run_sync_bg
}

run_sync() {
  DATE="$(studio_commander_date)"
  export DATE
  telegram_sync_begin "$DATE"
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
  telegram_sync_end
  echo "✅ Notion 동기화 (${elapsed}s) · ${DATE} — Telegram/Slack 최종 알림 1회"
}

run_sync_bg() {
  DATE="$(studio_commander_date)"
  export DATE
  telegram_sync_begin "$DATE"
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
}

run_intent_qc() {
  local intent="$1"
  shift || true
  studio_refresh_date
  DATE="$(studio_commander_date)"
  "$DIR/hermes-agent.sh" "$intent" --date "$DATE" --session "${CHAT_ID:-cli}" "$@"
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
  ls "$WORKDIR/content/newsletter/${DATE}"_newsletter_*.md >/dev/null 2>&1 && echo "✅ newsletter" || echo "⬜ newsletter"
  pgrep -f "hermes_cli.main gateway" >/dev/null && echo "✅ Gateway" || echo "❌ Gateway"
  echo ""
  echo "명령: /pipeline /research /content /newsletter /sync /morning /catch-up /publish /ask /studio"
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
        # qc research [keywords…] [--replace] [--approve]
        shift 2 || true
        if [[ $# -gt 0 ]]; then
          run_research_keyword "$@"
        else
          notify "[█░░░░] 1/5 리서치 시작"
          run_research
        fi
        ;;
      research-pending)
        run_research_pending
        ;;
      research-approve)
        shift 2 || true
        run_research_approve "${1:-}"
        ;;
      content)
        notify "[█░░░░] 1/5 콘텐츠 시작"
        run_content
        ;;
      newsletter)
        notify "[█░░░░] 1/5 뉴스레터 시작"
        run_newsletter
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
      morning)
        run_intent_qc morning
        ;;
      catch-up|catchup)
        run_intent_qc catch-up --days 3
        ;;
      publish)
        run_intent_qc publish linkedin
        ;;
      deep)
        echo "ℹ️ /deep는 주제가 필요합니다."
        echo "예: 자연어 'AX 트렌드 심층' 또는 hermes-agent.sh deep '주제'"
        ;;
      ask)
        if [[ -n "${ACTION:-}" ]]; then
          "$DIR/hermes-agent.sh" ask "$ACTION" --date "$DATE" --session "${CHAT_ID:-cli}"
        else
          echo "ℹ️ /ask는 질문이 필요합니다."
          echo "예: 자연어 'Kurly 인사이트 뭐였지' 또는 hermes-agent.sh ask '질문'"
        fi
        ;;
      pending)
        run_intent_qc pending
        ;;
      linkedin)
        run_intent_qc linkedin
        ;;
      blog)
        "$DIR/run-blog-pipeline.sh" "$DATE" --validate
        ;;
      traces)
        run_intent_qc traces --days 7
        ;;
      handoff)
        run_intent_qc handoff --days 7
        ;;
      graph)
        run_intent_qc graph --days 14
        ;;
      commands)
        run_intent_qc commands
        ;;
      approve)
        run_intent_qc approve all
        ;;
      coach)
        run_intent_qc coach
        ;;
      agents-eval|agents)
        "$DIR/agents-eval.sh" "$DATE"
        ;;
      audit)
        run_intent_qc audit
        ;;
      instagram)
        run_intent_qc instagram
        ;;
      wiki)
        run_intent_qc wiki seed
        ;;
      squad)
        echo "ℹ️ /squad는 주제가 필요합니다."
        echo "예: hermes-agent.sh squad 'AX 트렌드' --date $DATE"
        ;;
      watch)
        run_intent_qc watch
        ;;
      supervised)
        echo "ℹ️ /supervised는 ~60s+ 소요 — 터미널 권장"
        echo "실행: SKIP_NEWSLETTER=1 SKIP_NOTION_ARCHIVE=1 $DIR/run-supervised-pipeline.sh $DATE"
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
      intent-pack)
        detect_intent_pack "$MSG"
        ;;
      agents-eval)
        "$DIR/agents-eval.sh" "$DATE"
        ;;
      research-approve)
        run_research_approve
        ;;
      research-pending)
        run_research_pending
        ;;
      research)
        mapfile -t RARGS < <(parse_research_args "$MSG")
        if [[ ${#RARGS[@]} -gt 0 ]]; then
          run_research_keyword "${RARGS[@]}"
        else
          run_research
        fi
        ;;
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
  morning)
    "$DIR/hermes-agent.sh" morning --date "$DATE" --session "${CHAT_ID:-cli}"
    ;;
  catch-up|catchup)
    "$DIR/hermes-agent.sh" catch-up --date "$DATE" --session "${CHAT_ID:-cli}"
    ;;
  publish)
    CH="${ACTION:-linkedin}"
    "$DIR/hermes-agent.sh" publish "$CH" --date "$DATE" --session "${CHAT_ID:-cli}"
    ;;
  deep)
    "$DIR/hermes-agent.sh" deep "${ACTION:-}" --date "$DATE" --session "${CHAT_ID:-cli}"
    ;;
  ask)
    "$DIR/hermes-agent.sh" route "${ACTION:-}" --date "$DATE" --session "${CHAT_ID:-cli}"
    ;;
  proactive)
    "$DIR/hermes-agent.sh" proactive --date "$DATE"
    ;;
  bridge-sync)
    "$DIR/hermes-agent.sh" bridge-sync --date "$DATE"
    ;;
  research)  notify "[█░░░░] 1/5"; run_research ;;
  content)   notify "[█░░░░] 1/5"; run_content ;;
  pipeline)  run_pipeline ;;
  sync)      run_sync ;;
  sync-bg)   run_sync_bg ;;
  status|studio) run_status ;;
  *)
    echo "Usage: $0 {pipeline|research|content|sync|morning|catch-up|publish|deep|ask|proactive|status|qc|auto} [args]"
    exit 1
    ;;
esac
