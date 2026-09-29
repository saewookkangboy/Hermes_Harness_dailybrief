#!/usr/bin/env bash
# Meta Ads 루프 cron 등록 — 피로도 감시(매일) · 주간 리포트(월)
#
# 안전장치: config/meta-ads.yaml mode 가 api 이고 토큰이 있을 때만 등록합니다.
# sample 모드에서는 등록하지 않아 샘플 수치가 Slack 에 게시되지 않습니다.
#
# Usage: ./scripts/setup-meta-ads-cron.sh [--dry-run]
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_SCRIPTS="$HOME/.hermes/scripts"
DRY=0; [[ "${1:-}" == "--dry-run" ]] && DRY=1
# shellcheck source=lib/slack_home.sh
source "$WORKDIR/scripts/lib/slack_home.sh"

# 설정을 못 읽으면 여기서 멈춤 (아래 non-api 분기에 들어가 기존 작업을 지우지 않게)
if ! CFG_LINE=$(python3 - <<PY
import sys
sys.path.insert(0, "$WORKDIR/scripts")
from lib.meta_ads import load_config
c = load_config()
n = c.get("notify", {})
print(c["mode"], n.get("schedule_fatigue", "0 9 * * *").replace(" ", "_"), n.get("schedule_weekly", "5 9 * * 1").replace(" ", "_"))
PY
); then
  echo "❌ config/meta-ads.yaml 을 읽지 못해 아무것도 바꾸지 않았습니다"; exit 1
fi
read -r MODE FATIGUE_CRON WEEKLY_CRON <<< "$CFG_LINE"
FATIGUE_CRON="${FATIGUE_CRON//_/ }"; WEEKLY_CRON="${WEEKLY_CRON//_/ }"

# `hermes cron list` 출력: "  <id> [active]" 다음 줄들에 "    Name:      <name>"
# 이름은 정확히 같을 때만 (cron-meta-weekly 가 cron-meta-weekly-backup 을 지우지 않게)
_job_ids() {
  local name="$1" out
  # 조회 실패를 "작업 없음"으로 보면 아래 create 가 중복 작업을 만듭니다
  out=$(hermes cron list) || { echo "❌ hermes cron list 실패 — 아무것도 바꾸지 않고 중단" >&2; return 1; }
  awk -v n="$name" '
    /^  [a-f0-9][a-f0-9]/ { id=$1; gsub(/[^a-f0-9]/,"",id) }
    /^[[:space:]]*Name:/ { v=$0; sub(/^[[:space:]]*Name:[[:space:]]*/,"",v); sub(/[[:space:]]+$/,"",v); if (v==n && id!="") print id }
  ' <<< "$out"
}
_remove() {
  local name="$1" id ids
  ids=$(_job_ids "$name") || return 1
  for id in $ids; do
    if [[ "$DRY" == "1" ]]; then echo "[dry-run] remove $name ($id)"; continue; fi
    if ! hermes cron remove "$id" >/dev/null; then
      echo "❌ $name ($id) 해제 실패 — 중복 등록을 막으려고 중단" >&2; return 1
    fi
    echo "  🗑  $name ($id) 해제"
  done
}

echo "=== Meta Ads cron (조회 전용) ==="
echo "mode: $MODE · fatigue: $FATIGUE_CRON · weekly: $WEEKLY_CRON"
if [[ "$MODE" != "api" ]]; then
  echo "ℹ️  mode=$MODE — 등록하지 않습니다. 토큰 연결 후 config/meta-ads.yaml mode: api 로 바꾸고 다시 실행하세요."
  # api 모드에서 등록했던 작업이 남아 있으면 해제 (sample 로 되돌린 뒤 샘플 수치가 게시되지 않게)
  _remove "cron-meta-fatigue" || exit 1
  _remove "cron-meta-weekly" || exit 1
  exit 0
fi

# 토큰 확인은 실제 조회 1회로 합니다 (쓰기 없음)
if ! PROBE=$(python3 "$WORKDIR/scripts/meta-ads.py" fatigue --date "$(date +%Y-%m-%d)-probe" 2>&1); then
  echo "❌ Meta 조회 실패 — 등록 중단"; echo "$PROBE"; exit 1
fi

NAME="$(studio_slack_home_channel_name 2>/dev/null || true)"
DELIVER="${META_ADS_DELIVER:-${NAME:+slack:#${NAME}}}"
DELIVER="${DELIVER:-telegram}"
echo "deliver: $DELIVER"

if [[ "$DRY" == "1" ]]; then
  echo "[dry-run] cron-meta-fatigue ($FATIGUE_CRON) · cron-meta-weekly ($WEEKLY_CRON)"
  exit 0
fi

mkdir -p "$HERMES_SCRIPTS"
cp "$WORKDIR/scripts/lib/cron_bootstrap.sh" "$HERMES_SCRIPTS/cron_bootstrap.sh"
for s in cron-meta-fatigue.sh cron-meta-weekly.sh; do
  cp "$WORKDIR/scripts/$s" "$HERMES_SCRIPTS/$s"; chmod +x "$HERMES_SCRIPTS/$s"
done

_create() {
  local name="$1" schedule="$2" script="$3"
  _remove "$name" || exit 1
  hermes cron create --name "$name" --workdir "$WORKDIR" --script "$script" \
    --no-agent --deliver "$DELIVER" "$schedule" "" && echo "  ✅ $name"
}
_create "cron-meta-fatigue" "$FATIGUE_CRON" "cron-meta-fatigue.sh"
_create "cron-meta-weekly" "$WEEKLY_CRON" "cron-meta-weekly.sh"
