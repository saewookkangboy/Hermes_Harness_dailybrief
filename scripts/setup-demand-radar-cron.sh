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

# 설정을 못 읽으면 여기서 멈춤 (빈 MODE 로 아래 non-api 분기에 들어가 기존 작업을 지우지 않게)
if ! CFG_LINE=$(python3 - <<PY
import sys
sys.path.insert(0, "$WORKDIR/scripts")
from lib.demand_radar import load_config
c = load_config()
print(c["mode"], (c.get("notify") or {}).get("schedule", "40 8 * * 1").replace(" ", "_"))
PY
); then
  echo "❌ config/demand-radar.yaml 을 읽지 못해 아무것도 바꾸지 않았습니다"; exit 1
fi
read -r MODE SCHEDULE <<< "$CFG_LINE"
SCHEDULE="${SCHEDULE//_/ }"

# `hermes cron list` 출력: "  <id> [active]" 다음 줄들에 "    Name:      <name>"
# 이름은 정확히 같을 때만 (cron-demand-radar-old 같은 다른 작업은 건드리지 않게)
_job_ids() {
  local name="$1" out
  # 조회 실패를 "작업 없음"으로 보면 아래 create 가 중복 작업을 만듭니다
  out=$(hermes cron list) || { echo "❌ hermes cron list 실패 — 아무것도 바꾸지 않고 중단" >&2; return 1; }
  awk -v n="$name" '
    /^  [a-f0-9][a-f0-9]/ { id=$1; gsub(/[^a-f0-9]/,"",id) }
    /^[[:space:]]*Name:/ { v=$0; sub(/^[[:space:]]*Name:[[:space:]]*/,"",v); sub(/[[:space:]]+$/,"",v); if (v==n && id!="") print id }
  ' <<< "$out"
}
_remove_existing() {
  local id ids
  ids=$(_job_ids "cron-demand-radar") || return 1
  for id in $ids; do
    if [[ "$DRY" == "1" ]]; then echo "[dry-run] remove cron-demand-radar ($id)"; continue; fi
    if ! hermes cron remove "$id" >/dev/null; then
      echo "❌ cron-demand-radar ($id) 해제 실패 — 중복 등록을 막으려고 중단" >&2; return 1
    fi
    echo "  🗑  cron-demand-radar ($id) 해제"
  done
}

echo "=== Demand Radar cron (조회 전용) ==="
echo "mode: $MODE · schedule: $SCHEDULE"
if [[ "$MODE" != "api" ]]; then
  echo "ℹ️  mode=$MODE — 등록하지 않습니다. 키 연결 후 config/demand-radar.yaml mode: api 로 바꾸고 다시 실행하세요."
  _remove_existing || exit 1   # api 모드에서 등록했던 작업이 남아 있으면 해제
  exit 0
fi

if ! PROBE=$(python3 "$WORKDIR/scripts/demand-radar.py" --probe 2>&1); then
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

_remove_existing || exit 1
hermes cron create --name "cron-demand-radar" --workdir "$WORKDIR" --script "cron-demand-radar.sh" \
  --no-agent --deliver "$DELIVER" "$SCHEDULE" "" && echo "  ✅ cron-demand-radar"
