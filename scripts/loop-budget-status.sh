#!/usr/bin/env bash
# 오늘 cost-ledger spend vs yaml cap (결정적, read-only)
#
# Usage: ./loop-budget-status.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

python3 - <<PY
import sys

sys.path.insert(0, "$DIR")
from lib.content_quality_config import budget_config
from lib.loop_budget import (
    check_loop_budget,
    is_near_cap,
    read_today_spend,
    read_today_spend_by_path,
    warn_threshold_pct,
)

cfg = budget_config()
tokens, usd = read_today_spend()
token_cap = int(cfg.get("daily_token_cap") or 0)
usd_cap = float(cfg.get("daily_usd_cap") or 0.0)
st = check_loop_budget()

print("=== Loop Budget Status ===")
print(f"tokens_today: {tokens:,}" + (f" / {token_cap:,}" if token_cap else ""))
print(f"usd_today:    {usd:.2f}" + (f" / {usd_cap:.2f}" if usd_cap else ""))
print(f"check:        {st.detail}")
if token_cap and is_near_cap(tokens, token_cap):
    print(f"warn:         >= {warn_threshold_pct()}% of daily token cap")
if st.path:
    print(f"path:         {st.path} {st.path_tokens:,} / {st.path_token_cap:,}")

by_path = read_today_spend_by_path()
if by_path:
    print("by_path:")
    for path in sorted(by_path):
        pt, pu = by_path[path]
        line = f"  {path}: {pt:,} tokens"
        if pu:
            line += f", ${pu:.2f}"
        path_caps = cfg.get("path_daily_token_caps") or {}
        if path in path_caps:
            line += f" (cap {int(path_caps[path]):,})"
        print(line)
PY
