#!/usr/bin/env bash
# 단계별 토큰·비용 집계 리포트
set -euo pipefail
STUDIO="${HERMES_STUDIO:-${HERMES_WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
cd "$STUDIO"

SINCE="7d"
STAGE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --since) SINCE="$2"; shift 2 ;;
    --stage) STAGE="$2"; shift 2 ;;
    -h|--help) echo "usage: cost-report.sh [--since 7d|24h|YYYY-MM-DD] [--stage NAME]"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

python3 - "$SINCE" "$STAGE" <<'PY'
import sys
sys.path.insert(0, "scripts")
from lib import ledger

since, stage = sys.argv[1], sys.argv[2] or None
agg = ledger.aggregate(since)
if stage:
    agg = {k: v for k, v in agg.items() if k == stage}

if not agg:
    print(f"(원장에 데이터 없음: since={since})")
    raise SystemExit(0)

print(f"\n비용 리포트 — since={since}\n")
print(f"{'stage':<28}{'runs':>6}{'avg_in':>9}{'avg_out':>9}{'max_in':>9}{'cost($)':>10}  det")
print("-" * 82)
for name, s in sorted(agg.items(), key=lambda kv: -kv[1]["cost_usd"]):
    det = "✓" if s["deterministic"] else ""
    print(f"{name:<28}{s['runs']:>6}{s['avg_in']:>9}{s['avg_out']:>9}"
          f"{s['max_in']:>9}{s['cost_usd']:>10.3f}  {det}")
total = sum(s["cost_usd"] for s in agg.values())
print("-" * 82)
print(f"{'TOTAL':<28}{'':>6}{'':>9}{'':>9}{'':>9}{total:>10.3f}\n")
PY
