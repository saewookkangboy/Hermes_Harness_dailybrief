#!/usr/bin/env bash
# 결정적 Commander cron — 모닝 브리핑 · 헬스 알림 (--no-agent)
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
HERMES_SCRIPTS="$HOME/.hermes/scripts"
DELIVER="${CRON_DELIVER:-telegram}"

echo "=== Commander Cron (결정적, LLM 없음) ==="

mkdir -p "$HERMES_SCRIPTS"
chmod +x "$WORKDIR/scripts/cron-morning-brief.sh" "$WORKDIR/scripts/cron-health-alert.sh" \
  "$WORKDIR/scripts/cron-daily-content-triage.sh" "$WORKDIR/scripts/cron-supervised-pipeline.sh"

# Hermes cron: symlink 불가 — 실제 파일 복사 (~/.hermes/scripts/ containment)
rm -f "$HERMES_SCRIPTS/cron-morning-brief.sh" "$HERMES_SCRIPTS/cron-health-alert.sh" \
  "$HERMES_SCRIPTS/cron-daily-content-triage.sh" "$HERMES_SCRIPTS/cron-supervised-pipeline.sh"
cp "$WORKDIR/scripts/cron-morning-brief.sh" "$HERMES_SCRIPTS/cron-morning-brief.sh"
cp "$WORKDIR/scripts/cron-health-alert.sh" "$HERMES_SCRIPTS/cron-health-alert.sh"
cp "$WORKDIR/scripts/cron-daily-content-triage.sh" "$HERMES_SCRIPTS/cron-daily-content-triage.sh"
cp "$WORKDIR/scripts/cron-supervised-pipeline.sh" "$HERMES_SCRIPTS/cron-supervised-pipeline.sh"
chmod +x "$HERMES_SCRIPTS/cron-morning-brief.sh" "$HERMES_SCRIPTS/cron-health-alert.sh" \
  "$HERMES_SCRIPTS/cron-daily-content-triage.sh" "$HERMES_SCRIPTS/cron-supervised-pipeline.sh"

_remove_by_name() {
  local name="$1" id ids
  ids=$(hermes cron list 2>/dev/null | awk -v n="$name" '
    /^  [a-f0-9][a-f0-9]/ { id=$1; gsub(/[^a-f0-9]/,"",id) }
    $0 ~ "Name:" && index($0,n)>0 { if (id!="") print id }
  ' || true)
  for id in $ids; do
    hermes cron remove "$id" 2>/dev/null && echo "  제거: $name ($id)" || true
  done
}

_create() {
  local name="$1" schedule="$2" script="$3"
  _remove_by_name "$name"
  echo "등록: $name ($schedule) → deliver=$DELIVER"
  if ! hermes cron create \
    --name "$name" \
    --workdir "$WORKDIR" \
    --script "$script" \
    --no-agent \
    --deliver "$DELIVER" \
    "$schedule" ""; then
    echo "  ❌ $name 실패" >&2
    return 1
  fi
  echo "  ✅ $name"
}

_create "cron-morning-brief" "0 9 * * 1-5" "cron-morning-brief.sh"
_create "cron-daily-triage" "30 9 * * 1-5" "cron-daily-content-triage.sh"
_create "cron-supervised-pipeline" "0 10 * * 1-5" "cron-supervised-pipeline.sh"
_create "cron-health-alert" "0 10,18 * * *" "cron-health-alert.sh"

chmod +x "$WORKDIR/scripts/cron-weekly-graph-digest.sh"
cp "$WORKDIR/scripts/cron-weekly-graph-digest.sh" "$HERMES_SCRIPTS/cron-weekly-graph-digest.sh"
chmod +x "$HERMES_SCRIPTS/cron-weekly-graph-digest.sh"
_create "cron-weekly-graph" "0 9 * * 1" "cron-weekly-graph-digest.sh"

chmod +x "$WORKDIR/scripts/cron-publish-schedule.sh"
cp "$WORKDIR/scripts/cron-publish-schedule.sh" "$HERMES_SCRIPTS/cron-publish-schedule.sh"
chmod +x "$HERMES_SCRIPTS/cron-publish-schedule.sh"
_create "cron-publish-schedule" "*/15 * * * *" "cron-publish-schedule.sh"

chmod +x "$WORKDIR/scripts/cron-competitive-watch.sh"
cp "$WORKDIR/scripts/cron-competitive-watch.sh" "$HERMES_SCRIPTS/cron-competitive-watch.sh"
chmod +x "$HERMES_SCRIPTS/cron-competitive-watch.sh"
_create "cron-competitive-watch" "0 9 * * 1" "cron-competitive-watch.sh"

echo ""
hermes cron list 2>/dev/null | grep -E "cron-morning|cron-daily-triage|cron-supervised|cron-health|cron-weekly|cron-publish|cron-competitive" || echo "⚠️  Commander cron 미표시 — hermes cron list 확인"
