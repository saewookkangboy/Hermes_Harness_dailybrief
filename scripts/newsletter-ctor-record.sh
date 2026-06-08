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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --delivered) DELIVERED="$2"; shift 2 ;;
    --opens) OPENS="$2"; shift 2 ;;
    --clicks) CLICKS="$2"; shift 2 ;;
    --notes) NOTES="$2"; shift 2 ;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) STAMP="$1"; shift ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$STAMP" && -n "$DELIVERED" && -n "$OPENS" && -n "$CLICKS" ]] || {
  echo "Usage: $0 YYYY-MM-DD --delivered N --opens N --clicks N [--notes text]" >&2
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
    notes="${NOTES}",
)
print(f"✅ CTOR recorded · {row['stamp']}")
print(f"   Open {row['open_rate_pct']}% · CTOR {row['ctor_pct']}% · {row['ctor_health']}")
PY
