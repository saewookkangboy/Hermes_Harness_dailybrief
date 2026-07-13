#!/usr/bin/env bash
# 주간 staging supervised 검증 — naturalness blocking 회귀 (결정적, LLM 없음)
#
# hermes cron: 토 11:00 (setup-commander-cron.sh)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
SCRIPTS_DIR="$WORKDIR/scripts"
# shellcheck source=lib/studio-date.sh
source "$SCRIPTS_DIR/lib/studio-date.sh"

STAMP="$(studio_commander_date)"
export HERMES_SUPERVISED_STAGING=1
export HERMES_CRON_SKIP_NOTION=1

echo "=== Weekly Staging Supervised · $STAMP ==="
"$SCRIPTS_DIR/staging-supervised-eval.sh" "$STAMP"
