#!/usr/bin/env bash
# Meta 피로도 감시 cron — 매일 09:00 (조회 전용, 결정적, LLM 0회)
# stdout 은 hermes cron --deliver slack:#<홈 채널> 로 게시. 대상 0개면 빈 출력 → 게시 없음.
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
# shellcheck source=lib/cron_bootstrap.sh
source "$WORKDIR/scripts/lib/cron_bootstrap.sh"

cron_run_py "$SCRIPTS_DIR/meta-ads.py" fatigue --require-api
