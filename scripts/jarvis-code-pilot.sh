#!/usr/bin/env bash
# JARVIS CODE macOS 파일럿 — 설치·호환성 검증 (Hermes 본체 비침투)
#
# Usage:
#   ./jarvis-code-pilot.sh              # prereq + install dry-run
#   JARVIS_CODE_PILOT_INSTALL=1 ./jarvis-code-pilot.sh  # 실제 install (선택)
#   JARVIS_CODE_NO_MODEL_PRELOAD=1 ...  # bge-m3 다운로드 생략
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
LOG_DIR="$WORKDIR/content/logs"
DATE="${DATE:-$(date +%Y-%m-%d)}"
REPORT="$LOG_DIR/${DATE}_jarvis-code-pilot.md"
INSTALL="${JARVIS_CODE_PILOT_INSTALL:-0}"
NO_MODEL="${JARVIS_CODE_NO_MODEL_PRELOAD:-1}"

mkdir -p "$LOG_DIR"

PASS=0
FAIL=0
WARN=0

record() {
  case "$1" in
    PASS) PASS=$((PASS + 1)) ;;
    FAIL) FAIL=$((FAIL + 1)) ;;
    WARN) WARN=$((WARN + 1)) ;;
  esac
  echo "$1 $2"
}

echo "=== JARVIS CODE macOS Pilot ==="

OS=$(uname -s)
ARCH=$(uname -m)
record PASS "platform ${OS}/${ARCH}"

# Prerequisites
for cmd in git curl python3; do
  if command -v "$cmd" >/dev/null 2>&1; then
    record PASS "prereq_${cmd}"
  else
    record FAIL "prereq_${cmd}_missing"
  fi
done

if command -v node >/dev/null 2>&1; then
  record PASS "prereq_node=$(node -v 2>/dev/null || echo ok)"
else
  record WARN "prereq_node_missing (installer may bundle)"
fi

# Install script fetch
INSTALL_URL="https://raw.githubusercontent.com/jarvis-llm-codec/jarvis-code/main/install.sh"
INSTALL_SCRIPT="/tmp/jarvis-code-install-$$.sh"
if curl -fsSL "$INSTALL_URL" -o "$INSTALL_SCRIPT" 2>/dev/null; then
  record PASS "install_script_fetch"
  if grep -q "is_macos" "$INSTALL_SCRIPT"; then
    record PASS "install_macos_support"
  else
    record FAIL "install_macos_support"
  fi
else
  record FAIL "install_script_fetch"
fi

JARVIS_BIN=""
if command -v jarvis >/dev/null 2>&1; then
  JARVIS_BIN=$(command -v jarvis)
  record PASS "jarvis_already_installed=${JARVIS_BIN}"
elif [[ -x "$HOME/.local/bin/jarvis" ]]; then
  JARVIS_BIN="$HOME/.local/bin/jarvis"
  record PASS "jarvis_local_bin"
fi

if [[ "$INSTALL" == "1" && -z "$JARVIS_BIN" && -f "$INSTALL_SCRIPT" ]]; then
  echo "--- Running install (JARVIS_CODE_NO_MODEL_PRELOAD=$NO_MODEL) ---"
  export JARVIS_CODE_NO_MODEL_PRELOAD="$NO_MODEL"
  export npm_config_allow_remote=true
  if bash "$INSTALL_SCRIPT" 2>&1 | tee "/tmp/jarvis-code-install.log"; then
    if [[ -x "$HOME/.local/bin/jarvis" ]]; then
      JARVIS_BIN="$HOME/.local/bin/jarvis"
      record PASS "jarvis_install_ok"
    else
      record FAIL "jarvis_install_no_binary"
    fi
  else
    record FAIL "jarvis_install_failed"
  fi
else
  record PASS "install_skipped (set JARVIS_CODE_PILOT_INSTALL=1 to install)"
fi

# Version / help smoke
if [[ -n "$JARVIS_BIN" ]]; then
  if "$JARVIS_BIN" --help >/tmp/jarvis-help.log 2>&1 || "$JARVIS_BIN" -h >/tmp/jarvis-help.log 2>&1; then
    record PASS "jarvis_cli_help"
  else
    record WARN "jarvis_cli_help"
  fi
fi

# Hermes JARVIS.md cross-check
if [[ -f "$WORKDIR/JARVIS.md" ]]; then
  record PASS "hermes_jarvis_md"
else
  record FAIL "hermes_jarvis_md"
fi

rm -f "$INSTALL_SCRIPT"

# Report
{
  echo "# JARVIS CODE macOS Pilot — $DATE"
  echo ""
  echo "| Result | Count |"
  echo "|--------|-------|"
  echo "| PASS | $PASS |"
  echo "| WARN | $WARN |"
  echo "| FAIL | $FAIL |"
  echo ""
  echo "## Environment"
  echo "- Platform: \`$OS/$ARCH\`"
  echo "- Install attempted: \`$INSTALL\`"
  echo "- Model preload skipped: \`$NO_MODEL\`"
  echo "- jarvis binary: \`${JARVIS_BIN:-none}\`"
  echo ""
  echo "## Recommendation"
  if [[ "$FAIL" -eq 0 && -n "$JARVIS_BIN" ]]; then
    echo "파일럿 OK — 외부 레포(marketers-brain 등)에서 \`jarvis\` 코딩 세션 시험 가능."
  elif [[ "$FAIL" -eq 0 ]]; then
    echo "Prereq OK — \`JARVIS_CODE_PILOT_INSTALL=1 JARVIS_CODE_NO_MODEL_PRELOAD=1 ./scripts/jarvis-code-pilot.sh\` 로 설치 후 재검증."
  else
    echo "파일럿 FAIL — Hermes M1~M5는 영향 없음. macOS/Intel 호환 이슈 확인 필요."
  fi
} > "$REPORT"

echo ""
echo "Report: $REPORT"
echo "=== Summary: $PASS pass, $WARN warn, $FAIL fail ==="
[[ "$FAIL" -eq 0 ]]
