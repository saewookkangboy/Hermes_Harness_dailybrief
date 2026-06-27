#!/usr/bin/env bash
# LLM Wiki Ingest — research/raw 신규 소스 → wiki (비동기·옵션)
#
# Usage: HERMES_WIKI_INGEST=1 ./run-wiki-ingest.sh [파일명]
# 전략: docs/LLM-WIKI-INTEGRATION.md (M1 SLA 경로에 끼워 넣지 않음)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
RAW="$WORKDIR/content/research/raw"
TARGET="${1:-}"

if [[ "${HERMES_WIKI_INGEST:-0}" != "1" ]]; then
  echo "ℹ️  HERMES_WIKI_INGEST=1 필요 (일별 파이프라인 기본 off)" >&2
  exit 0
fi

mkdir -p "$RAW" "$WORKDIR/content/wiki/concepts" "$WORKDIR/content/wiki/entities"

if [[ -n "$TARGET" ]]; then
  SRC="$RAW/$TARGET"
else
  SRC=$(find "$RAW" -maxdepth 1 -type f ! -name '.gitkeep' 2>/dev/null | head -1)
fi

if [[ -z "$SRC" || ! -f "$SRC" ]]; then
  echo "❌ ingest 대상 없음: $RAW" >&2
  exit 1
fi

PROMPT="docs/LLM-WIKI-INTEGRATION.md 와 skills/shared/wiki-maintainer/SKILL.md Ingest 워크플로를 따르세요.
소스: ${SRC}
1) wiki/sources/ 요약 페이지
2) wiki/index.md 갱신
3) 관련 concepts/entities 교차참조
4) wiki/log.md append
M1 brief SoT는 수정하지 마세요."

HERMES_TOOLSETS=hermes-cli HERMES_USE_CODEX=1 "$DIR/hermes-run.sh" \
  "$PROMPT" --skills wiki-maintainer -t hermes-cli

echo "✅ Wiki Ingest 요청 완료: $SRC"
