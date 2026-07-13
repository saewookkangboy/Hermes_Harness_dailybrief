#!/usr/bin/env bash
# Bootstrap all Hermes sibling studios (Tier 1–3)
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/bootstrap-hermes-studios.py" "$@"
