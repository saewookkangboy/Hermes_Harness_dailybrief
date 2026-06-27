#!/usr/bin/env bash
# M4 외부 채널 메트릭 import (LinkedIn/GA4 JSON export)
#
# Usage: ./m4-import-metrics.sh linkedin /path/to/metrics.json
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
CHANNEL="${1:?channel required (e.g. linkedin)}"
JSON_PATH="${2:?json path required}"

run_py() {
  if [[ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]]; then
    "$HOME/.hermes/hermes-agent/venv/bin/python" "$@"
  else
    python3 "$@"
  fi
}

run_py -c "
import sys
from pathlib import Path
sys.path.insert(0, '$DIR')
from lib.m4_channel_metrics import import_external_metrics
r = import_external_metrics(Path('$JSON_PATH'), '$CHANNEL')
import json
print(json.dumps(r, ensure_ascii=False, indent=2))
"
