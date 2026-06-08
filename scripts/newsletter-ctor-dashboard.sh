#!/usr/bin/env bash
# CTOR 실측 대시보드 생성 (HTML + MD)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="${1:-$(date +%Y-%m-%d)}"

python3 <<PY
import sys
sys.path.insert(0, "${DIR}")
from lib.newsletter_ctor import write_dashboard_outputs
md, html = write_dashboard_outputs("${STAMP}")
print(f"📊 Dashboard MD:   {md}")
print(f"📊 Dashboard HTML: {html}")
PY
