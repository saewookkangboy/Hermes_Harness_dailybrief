#!/usr/bin/env bash
# LLM Wiki Lint — 모순·고아·stale 주간 점검 (비동기·옵션)
#
# Usage: HERMES_WIKI_LINT=1 ./run-wiki-lint.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
STAMP="${1:-$(studio_today)}"
REPORT="$WORKDIR/content/logs/${STAMP}_wiki-lint-report.md"

if [[ "${HERMES_WIKI_LINT:-0}" != "1" ]]; then
  echo "ℹ️  HERMES_WIKI_LINT=1 필요 (주간 배치 권장)" >&2
  exit 0
fi

PROMPT="skills/shared/wiki-maintainer/SKILL.md Lint 워크플로를 실행하세요.
content/wiki/concepts, entities, index.md 전수 스캔.
리포트: ${REPORT}
wiki/log.md append: ## [${STAMP}] lint | ..."

HERMES_TOOLSETS=hermes-cli HERMES_USE_CODEX=1 "$DIR/hermes-run.sh" \
  "$PROMPT" --skills wiki-maintainer -t hermes-cli

echo "✅ Wiki Lint 요청 완료 → $REPORT"
