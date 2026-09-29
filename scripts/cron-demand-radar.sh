#!/usr/bin/env bash
# 네이버 데이터랩 수요 레이더 cron — 월요일 08:40 (조회 전용, 결정적, LLM 0회)
# stdout(급상승 키워드 제안)은 hermes cron --deliver slack:#<홈 채널> 로 게시. M1 자동 병합 없음.
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
# shellcheck source=lib/cron_bootstrap.sh
source "$WORKDIR/scripts/lib/cron_bootstrap.sh"

cron_run_py "$SCRIPTS_DIR/demand-radar.py" --require-api
