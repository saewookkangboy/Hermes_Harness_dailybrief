#!/usr/bin/env bash
# 뉴스레터 CTOR 실측 기록
# Usage: ./newsletter-ctor-record.sh 2026-06-08 --delivered 500 --opens 112 --clicks 14
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP=""
DELIVERED=""
OPENS=""
CLICKS=""
NOTES=""
REPLIES="0"
UNSUB="0"
PATTERN=""
SEED="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --delivered) DELIVERED="$2"; shift 2 ;;
    --opens) OPENS="$2"; shift 2 ;;
    --clicks) CLICKS="$2"; shift 2 ;;
    --replies) REPLIES="$2"; shift 2 ;;
    --unsub) UNSUB="$2"; shift 2 ;;
    --pattern) PATTERN="$2"; shift 2 ;;
    --seed) SEED="1"; shift ;;
    --notes) NOTES="$2"; shift 2 ;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) STAMP="$1"; shift ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$STAMP" && -n "$DELIVERED" && -n "$OPENS" && -n "$CLICKS" ]] || {
  echo "Usage: $0 YYYY-MM-DD --delivered N --opens N --clicks N \\" >&2
  echo "         [--replies N] [--unsub N] [--pattern id] [--seed] [--notes text]" >&2
  exit 1
}

python3 <<PY
import sys
sys.path.insert(0, "${DIR}")
from lib.newsletter_ctor import record_campaign
row = record_campaign(
    "${STAMP}",
    delivered=int("${DELIVERED}"),
    unique_opens=int("${OPENS}"),
    unique_clicks=int("${CLICKS}"),
    replies=int("${REPLIES}"),
    unsubscribes=int("${UNSUB}"),
    pattern_id="${PATTERN}",
    seed=True if "${SEED}" == "1" else None,
    notes="${NOTES}",
)
print(f"✅ CTOR recorded · {row['stamp']}" + (" [평가 시드 — 학습 제외]" if row["seed"] else ""))
print(f"   Open {row['open_rate_pct']}% · CTOR {row['ctor_pct']}% · CTR {row['ctr_pct']}%")
print(f"   회신 {row['reply_rate_pct']}% · 해지 {row['unsub_rate_pct']}% · {row['ctor_health']}")
print(f"   패턴: {row['pattern_id'] or '—'} · flags: {', '.join(row['health_flags'])}")
PY
