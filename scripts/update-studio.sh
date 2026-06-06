#!/usr/bin/env bash
# Hermes Content Studio — 전체 업데이트 + 검증
#
# Usage: ./update-studio.sh [--skip-hermes]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
SKIP_HERMES=0

for arg in "$@"; do
  [[ "$arg" == "--skip-hermes" ]] && SKIP_HERMES=1
done

echo "=== Hermes Content Studio 업데이트 (v1.2.0) ==="
echo ""

if [[ "$SKIP_HERMES" == "0" ]]; then
  echo "--- 1/4 Hermes Agent ---"
  hermes update -y
  echo ""
else
  echo "--- 1/4 Hermes Agent (skip) ---"
fi

echo "--- 2/4 Python 의존성 ---"
if [[ -x "$HERMES_PY" ]]; then
  "$HERMES_PY" -m pip install -q -r "$WORKDIR/requirements.txt"
else
  python3 -m pip install -q -r "$WORKDIR/requirements.txt"
fi

echo "--- 3/4 스크립트 실행 권한 ---"
chmod +x "$DIR"/*.sh 2>/dev/null || true

echo "--- 4/4 헬스체크 ---"
"$DIR/health-check.sh"

echo ""
echo "=== 업데이트 완료 ==="
echo "버전: $(grep 'version:' "$WORKDIR/config/studio.yaml" | head -1 | awk '{print $2}')"
echo "Hermes: $(hermes --version 2>/dev/null | head -1)"
echo ""
echo "빠른 검증:"
echo "  ~/hermes-content-studio/scripts/run-research-brief.sh"
echo "  ~/hermes-content-studio/scripts/run-pipeline.sh"
