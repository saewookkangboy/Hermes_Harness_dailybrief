#!/usr/bin/env bash
# 누적 개념 그래프 빌드 래퍼. 결정적 (LLM 0).
set -euo pipefail
STUDIO="${HERMES_STUDIO:-${HERMES_WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
cd "$STUDIO"

FORCE=0
ARGS=()
for a in "$@"; do
  if [[ "$a" == "--force" ]]; then
    FORCE=1
  else
    ARGS+=("$a")
  fi
done

if [[ "${HERMES_WIKI_GRAPH:-0}" != "1" && "$FORCE" != "1" ]]; then
  echo "(HERMES_WIKI_GRAPH=1 미설정 — 건너뜀)"
  exit 0
fi

START=$(date +%s)
# 밀리초 정밀 타이밍 (1초 해상도 SLA 오측정 방지)
START_MS=$(python3 -c 'import time; print(int(time.time()*1000))')
python3 scripts/build-graph.py "${ARGS[@]+"${ARGS[@]}"}"
END_MS=$(python3 -c 'import time; print(int(time.time()*1000))')
ELAPSED_MS=$(( END_MS - START_MS ))
ELAPSED=$(( (ELAPSED_MS + 999) / 1000 ))
echo "── wiki-graph: ${ELAPSED_MS}ms (~${ELAPSED}s)"

# SLA 가드: 증분 3초 / 전체 재빌드 10초 (초과 시 WARN, exit 0 유지)
LIMIT_MS=3000
[[ " ${ARGS[*]-} " == *" --rebuild "* ]] && LIMIT_MS=10000
if (( ELAPSED_MS > LIMIT_MS )); then
  echo "⚠ 그래프 빌드 SLA 초과 (${ELAPSED_MS}ms > ${LIMIT_MS}ms)" >&2
fi
