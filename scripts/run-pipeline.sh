#!/usr/bin/env bash
# Hermes Content Studio — 전체 파이프라인 (리서치 → 콘텐츠 → 강의 → Notion)
# Harness v1.2.0 — 결정적 우선, init + 타이밍 트레이스
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
REQUESTED_DATE="${1:-}"
DATE="${REQUESTED_DATE:-$(studio_today)}"
PIPELINE_START=$(date +%s)

# Harness bootstrap (헬스체크는 SKIP_INIT=1 로 건너뛰기)
if [[ "${SKIP_INIT:-0}" != "1" ]]; then
  "$DIR/init.sh" --skip-health 2>/dev/null || true
fi

echo "=== Pipeline 시작 ($DATE) ==="
"$DIR/run-research-brief.sh" "$DATE"
# 인자 없이 실행 시 자정 경계 후 content 날짜 재동기화
if [[ -z "$REQUESTED_DATE" ]]; then
  DATE="$(studio_today)"
fi
# M1 직후 brief SoT 재사용 (중복 gather 방지)
HERMES_SKIP_RESEARCH=1 "$DIR/run-content-package.sh" "$DATE"
# 강의 슬라이드 — /pipeline 제외 (/lecture 명령 사용)
# SKIP_LECTURE=0 으로만 파이프라인에 포함
if [[ "${SKIP_LECTURE:-1}" != "1" ]]; then
  LECTURE_ARGS=(--from-brief "$DATE")
  if [[ "${LECTURE_DESIGN_MODE:-}" == "claude-design" ]]; then
    LECTURE_ARGS+=(--design-mode claude-design --notion-sync)
  fi
  "$DIR/run-lecture-slides.sh" "${LECTURE_ARGS[@]}" || echo "⚠️  Lecture slides skipped"
fi
# Notion 아카이브 (실패해도 Telegram·로컬 산출물 유지)
if [[ "${SKIP_NOTION_ARCHIVE:-0}" != "1" ]]; then
  ARCHIVE_ARGS=(--force --notify-final)
  if [[ -n "${TELEGRAM_CHAT_ID:-}" ]]; then
    ARCHIVE_ARGS+=(--telegram-chat "$TELEGRAM_CHAT_ID")
  fi
  if [[ -n "${SLACK_HOME_CHANNEL:-}" ]]; then
    ARCHIVE_ARGS+=(--slack-channel "$SLACK_HOME_CHANNEL")
  fi
  "$DIR/archive-to-notion.sh" "$DATE" "${ARCHIVE_ARGS[@]}" \
    || echo "⚠️  Notion archive skipped (see content-studio.log)"
fi

PIPELINE_END=$(date +%s)
PIPELINE_ELAPSED=$(( PIPELINE_END - PIPELINE_START ))
echo ""
echo "=== Pipeline 완료: ${PIPELINE_ELAPSED}s ==="

# Harness trace 기록
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
if [[ -x "$HERMES_PY" ]]; then
  "$HERMES_PY" -c "
import sys
sys.path.insert(0, '$DIR/lib')
from harness import append_trace, check_regression
r = check_regression('full_pipeline', $PIPELINE_ELAPSED)
append_trace({'stage': 'full_pipeline', 'elapsed_seconds': $PIPELINE_ELAPSED, 'date': '$DATE', **r})
if r.get('regression'):
    print('⚠️  Pipeline SLA/regression — config/harness.yaml 확인')
" 2>/dev/null || true
fi
