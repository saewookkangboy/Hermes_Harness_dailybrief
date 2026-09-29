#!/usr/bin/env bash
# 수요 레이더 cron 등록 — 월요일 08:40
#
# 안전장치: config/demand-radar.yaml mode 가 api 이고 키가 있을 때만 등록합니다.
# sample 모드에서는 등록하지 않아 샘플 수치가 Slack 에 게시되지 않습니다.
#
# Usage: ./scripts/setup-demand-radar-cron.sh [--dry-run]
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_SCRIPTS="$HOME/.hermes/scripts"
DRY=0; [[ "${1:-}" == "--dry-run" ]] && DRY=1
# shellcheck source=lib/slack_home.sh
source "$WORKDIR/scripts/lib/slack_home.sh"

read -r MODE SCHEDULE < <(python3 - <<PY
import sys
sys.path.insert(0, "$WORKDIR/scripts")
from lib.demand_radar import load_config
c = load_config()
print(c["mode"], (c.get("notify") or {}).get("schedule", "40 8 * * 1").replace(" ", "_"))
PY
)
SCHEDULE="${SCHEDULE//_/ }"

echo "=== Demand Radar cron (조회 전용) ==="
echo "mode: $MODE · schedule: $SCHEDULE"
if [[ "$MODE" != "api" ]]; then
  echo "ℹ️  mode=$MODE — 등록하지 않습니다. 키 연결 후 config/demand-radar.yaml mode: api 로 바꾸고 다시 실행하세요."
  exit 0
fi

if ! PROBE=$(python3 "$WORKDIR/scripts/demand-radar.py" --date "$(date +%Y-%m-%d)-probe" 2>&1); then
  echo "❌ 데이터랩 조회 실패 — 등록 중단"; echo "$PROBE"; exit 1
fi

NAME="$(studio_slack_home_channel_name 2>/dev/null || true)"
DELIVER="${DEMAND_RADAR_DELIVER:-${NAME:+slack:#${NAME}}}"
DELIVER="${DELIVER:-telegram}"
echo "deliver: $DELIVER"
if [[ "$DRY" == "1" ]]; then
  echo "[dry-run] cron-demand-radar ($SCHEDULE)"
  exit 0
fi

mkdir -p "$HERMES_SCRIPTS"
cp "$WORKDIR/scripts/lib/cron_bootstrap.sh" "$HERMES_SCRIPTS/cron_bootstrap.sh"
cp "$WORKDIR/scripts/cron-demand-radar.sh" "$HERMES_SCRIPTS/cron-demand-radar.sh"
chmod +x "$HERMES_SCRIPTS/cron-demand-radar.sh"

for id in $(hermes cron list 2>/dev/null | awk '/^  [a-f0-9][a-f0-9]/ {i=$1; gsub(/[^a-f0-9]/,"",i)} $0 ~ "Name:" && index($0,"cron-demand-radar")>0 {print i}'); do
  hermes cron remove "$id" >/dev/null 2>&1 || true
done
hermes cron create --name "cron-demand-radar" --workdir "$WORKDIR" --script "cron-demand-radar.sh" \
  --no-agent --deliver "$DELIVER" "$SCHEDULE" "" && echo "  ✅ cron-demand-radar"
