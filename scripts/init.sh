#!/usr/bin/env bash
# Hermes Content Studio — Harness Bootstrap (init.sh)
#
# 세션 시작 시 실행: 의존성·서비스·헬스·하네스 상태 초기화
# 참조: Anthropic "Effective harnesses for long-running agents"
#
# Usage:
#   ./init.sh              # 기본 부트스트랩
#   ./init.sh --start      # 서비스 시작 포함
#   ./init.sh --skip-health  # 헬스체크 건너뛰기
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
START_SERVICES=0
SKIP_HEALTH=0

for arg in "$@"; do
  case "$arg" in
    --start) START_SERVICES=1 ;;
    --skip-health) SKIP_HEALTH=1 ;;
  esac
done

echo "=== Hermes Content Studio init.sh (Harness v1.2.0) ==="
echo "워크디렉: $WORKDIR"
echo ""

# ── 1. 하네스 디렉토리 ─────────────────────────────────────
mkdir -p "$WORKDIR/.harness/traces"
mkdir -p "$WORKDIR/content"/{research,blog,instagram,linkedin,newsletter,lectures,drafts/cursor-handoff}

if [[ ! -f "$WORKDIR/.harness/feature_list.json" ]]; then
  echo "⚠️  feature_list.json 없음 — config/harness.yaml 참조" >&2
fi

# ── 2. Python 의존성 ───────────────────────────────────────
echo "--- 1/5 Python 의존성 ---"
if [[ -x "$HERMES_PY" ]]; then
  "$HERMES_PY" -m pip install -q -r "$WORKDIR/requirements.txt" 2>/dev/null || true
else
  python3 -m pip install -q -r "$WORKDIR/requirements.txt" 2>/dev/null || true
fi

# ── 3. 스크립트 권한 ───────────────────────────────────────
echo "--- 2/5 스크립트 권한 ---"
chmod +x "$DIR"/*.sh 2>/dev/null || true

# ── 4. 서비스 (선택) ───────────────────────────────────────
if [[ "$START_SERVICES" == "1" ]]; then
  echo "--- 3/5 서비스 시작 ---"
  "$DIR/start-services.sh" || echo "⚠️  start-services 일부 실패" >&2
else
  echo "--- 3/5 서비스 (skip — --start 로 시작) ---"
  if ! pgrep -x ollama >/dev/null 2>&1; then
    echo "⚠️  Ollama 미실행 — Hermes polish 시 필요" >&2
  fi
  if ! pgrep -f "hermes_cli.main gateway" >/dev/null 2>&1; then
    echo "⚠️  Gateway 미실행 — Telegram 요청 불가" >&2
  fi
fi

# ── 5. 헬스체크 ────────────────────────────────────────────
if [[ "$SKIP_HEALTH" == "0" ]]; then
  echo "--- 4/5 헬스체크 ---"
  "$DIR/health-check.sh" || { echo "❌ 헬스체크 실패" >&2; exit 1; }
else
  echo "--- 4/5 헬스체크 (skip) ---"
fi

# ── 6. 하네스 상태 요약 ────────────────────────────────────
echo "--- 5/5 하네스 상태 ---"
if [[ -f "$WORKDIR/.harness/progress.md" ]]; then
  rg -m1 "현재 최우선" "$WORKDIR/.harness/progress.md" 2>/dev/null || true
fi
if command -v jq >/dev/null 2>&1 && [[ -f "$WORKDIR/.harness/feature_list.json" ]]; then
  ACTIVE=$(jq -r '.features[] | select(.status=="in_progress") | .id + ": " + .title' \
    "$WORKDIR/.harness/feature_list.json" 2>/dev/null | head -1)
  [[ -n "$ACTIVE" ]] && echo "활성 기능: $ACTIVE"
fi

echo ""
echo "=== init.sh 완료 ==="
echo "다음: cat .harness/progress.md"
echo "파이프라인: scripts/run-pipeline.sh"
echo "성능 eval: scripts/harness-eval.sh"
