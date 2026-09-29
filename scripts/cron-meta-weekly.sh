#!/usr/bin/env bash
# Meta 주간 리포트 cron — 월요일 09:05 (조회 전용, 결정적, LLM 0회)
# 리포트: content/ads/{date}_meta-weekly-report.md → 다음 archive-to-notion 실행 때 Notion 아카이브
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
# shellcheck source=lib/cron_bootstrap.sh
source "$WORKDIR/scripts/lib/cron_bootstrap.sh"

cron_run_py "$SCRIPTS_DIR/meta-ads.py" weekly
