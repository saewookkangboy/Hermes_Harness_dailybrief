#!/usr/bin/env bash
# Hermes Content Studio — 강의 슬라이드 생성 (HTML + PPTX + claude-design 연동)
#
# Usage:
#   ./run-lecture-slides.sh "AEO 실전" --content-file outline.txt --preset claude
#   ./run-lecture-slides.sh "AEO 실전" --content-file outline.txt \
#     --design-mode claude-design --notion-sync
#   ./run-lecture-slides.sh --from-brief 2026-06-05 --design-mode claude-design
#
# Env:
#   LECTURE_DESIGN_MODE=claude-design  (기본 design-mode)
#   TELEGRAM_CHAT_ID=...               (Notion sync 시 Permalink 전송)
#   SKIP_NOTION_ARCHIVE=1              (Notion 건너뛰기)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
SCRIPTS="$WORKDIR/scripts"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

DESIGN_MODE="${LECTURE_DESIGN_MODE:-basic}"
NOTION_SYNC=0
PY_ARGS=()

run_python() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-mode)
      DESIGN_MODE="$2"
      shift 2
      ;;
    --notion-sync)
      NOTION_SYNC=1
      shift
      ;;
    *)
      PY_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ "$DESIGN_MODE" == "claude-design" ]]; then
  NOTION_SYNC=1
  HAS_PRESET=0
  for ((i=0; i<${#PY_ARGS[@]}; i++)); do
    if [[ "${PY_ARGS[i]}" == "--preset" || "${PY_ARGS[i]}" == "-p" ]]; then
      HAS_PRESET=1
      break
    fi
  done
  if [[ "$HAS_PRESET" == "0" ]]; then
    PY_ARGS+=(--preset claude)
  fi
fi

cd "$WORKDIR"
chmod +x "$SCRIPTS/generate-lecture-slides.py" \
  "$SCRIPTS/polish-lecture-claude-design.sh" 2>/dev/null || true

notify() {
  local msg="$1"
  [[ -n "${TELEGRAM_CHAT_ID:-}" ]] || return 0
  "$SCRIPTS/telegram-notify.sh" "$TELEGRAM_CHAT_ID" "$msg" 2>/dev/null || true
}

echo "=== 1/3 강의 슬라이드 생성 (outline + PPTX + base HTML) ==="
echo "design-mode: $DESIGN_MODE"

META=$(run_python "$SCRIPTS/generate-lecture-slides.py" \
  --design-mode "$DESIGN_MODE" --json "${PY_ARGS[@]}")

eval "$(echo "$META" | run_python -c "
import json, sys
d = json.load(sys.stdin)
base = d.get('html_base', d['html'])
for k, v in [
    ('TOPIC', d['topic']),
    ('STAMP', d['stamp']),
    ('PRESET', d['preset']),
    ('OUTLINE', d['outline']),
    ('HTML', d['html']),
    ('PPTX', d['pptx']),
    ('BASE_HTML', base),
]:
    print(f\"{k}={v!r}\")
")"

"$SCRIPTS/validate-output.sh" lecture "$OUTLINE"
echo "✅ $OUTLINE"
echo "✅ $PPTX"
echo "✅ $BASE_HTML"

if [[ "$DESIGN_MODE" == "claude-design" ]]; then
  echo ""
  echo "=== 2/3 claude-design HTML 덱 (1920×1080) ==="
  notify "[██░░░] 2/3 claude-design HTML 덱 생성 중…
주제: $TOPIC"
  "$SCRIPTS/polish-lecture-claude-design.sh" \
    "$TOPIC" "$STAMP" "$OUTLINE" "$BASE_HTML" "$HTML" "$PPTX" "$PRESET"
  echo "✅ $HTML (claude-design)"
else
  echo "✅ $HTML"
fi

if [[ "${HERMES_ENHANCE:-0}" == "1" && "$DESIGN_MODE" != "claude-design" ]]; then
  echo ""
  echo "=== Hermes polish (선택) ==="
  HERMES_TOOLSETS=hermes-cli HERMES_USE_CODEX=1 "$SCRIPTS/hermes-run.sh" \
    "content-studio-slides: 생성된 강의 슬라이드 검토·발표자 노트 보강. getdesign.md 준수." \
    --skills content-studio-slides -t hermes-cli || true
fi

if [[ "$NOTION_SYNC" == "1" && "${SKIP_NOTION_ARCHIVE:-0}" != "1" ]]; then
  echo ""
  echo "=== 3/3 Notion 동기화 ==="
  notify "[███░░] 3/3 Notion 동기화 중…"
  ARCHIVE_ARGS=(--force)
  [[ -n "${TELEGRAM_CHAT_ID:-}" ]] && ARCHIVE_ARGS+=(--telegram-chat "$TELEGRAM_CHAT_ID")
  "$SCRIPTS/archive-to-notion.sh" "$STAMP" "${ARCHIVE_ARGS[@]}" || \
    echo "⚠️  Notion archive skipped (see content-studio.log)"
fi

echo ""
echo "=== 강의 슬라이드 완료 ==="
echo "  outline: $OUTLINE"
echo "  html:    $HTML"
echo "  pptx:    $PPTX"
if [[ "$DESIGN_MODE" == "claude-design" ]]; then
  echo "  base:    $BASE_HTML"
fi
