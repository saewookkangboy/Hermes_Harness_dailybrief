#!/usr/bin/env bash
# 토큰 예산 게이트 회귀 검출. harness-eval.sh가 호출.
set -euo pipefail
STUDIO="${HERMES_STUDIO:-${HERMES_WORKDIR:-$HOME/hermes-content-studio}}"
cd "$STUDIO"

SINCE="${1:-7d}"
echo "── token gate eval (since=$SINCE) ──"
PYTHONPATH=scripts python3 -m lib.token_budget "$SINCE"
