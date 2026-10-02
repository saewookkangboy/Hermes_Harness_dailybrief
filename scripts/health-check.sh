#!/usr/bin/env bash
# Hermes Content Studio — 헬스체크
set -euo pipefail

WORKDIR="${HERMES_WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HERMES_VENV_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
if [[ -x "$HERMES_VENV_PY" ]]; then PY="$HERMES_VENV_PY"; else PY="python3"; fi
if command -v hermes >/dev/null 2>&1; then HERMES_INSTALLED=1; else HERMES_INSTALLED=0; fi

PASS=0
FAIL=0
WARN=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "✅ $name"
    PASS=$((PASS + 1))
  else
    echo "❌ $name"
    FAIL=$((FAIL + 1))
  fi
}

warn() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "✅ $name"
    PASS=$((PASS + 1))
  else
    echo "⚠️  $name (선택)"
    WARN=$((WARN + 1))
  fi
}

# Hermes Agent 미설치 호스트에서는 결정적 파이프라인만 쓰므로 Hermes 의존 항목을 경고로 낮춤
hermes_check() {
  if [[ "$HERMES_INSTALLED" == "1" ]]; then
    check "$@"
  else
    warn "$1 (Hermes Agent 미설치)" "$2"
  fi
}

echo "=== Hermes Content Studio Health Check (Harness v1.3.0) ==="
echo "호스트: $(uname -m) / $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'unknown')"
echo "워크스페이스: $WORKDIR"
echo "Python: $PY"
echo ""

echo "--- Harness 5-Subsystem ---"
check "HARNESS.md" "test -f '$WORKDIR'/HARNESS.md"
check "harness.yaml" "test -f '$WORKDIR'/config/harness.yaml"
check "feature_list.json" "test -f '$WORKDIR'/.harness/feature_list.json"
check "progress.md" "test -f '$WORKDIR'/.harness/progress.md"
check "init.sh" "test -x '$WORKDIR'/scripts/init.sh"
check "harness-eval.sh" "test -x '$WORKDIR'/scripts/harness-eval.sh"
check "lib/harness.py" "test -f '$WORKDIR'/scripts/lib/harness.py"
check "studio v1.3.0" "grep -qE 'version: \"1\\.(2|3)\\.0\"' '$WORKDIR'/config/studio.yaml"

echo ""
echo "--- 핵심 서비스 ---"
hermes_check "Hermes CLI" "hermes --version"
check "Ollama 실행" "pgrep -x ollama"
check "Ollama API" "curl -sf http://127.0.0.1:11434/api/tags"
hermes_check "Hermes Gateway" "pgrep -f 'hermes_cli\.main gateway|gateway run( |\$)'"
check "gemma4 모델" "ollama list 2>/dev/null | grep gemma4"
warn "Codex OAuth" "hermes auth status openai-codex 2>&1 | grep -q 'logged in'"
warn "Codex CLI" "test -x $HOME/.hermes/node/bin/codex || command -v codex"

echo ""
echo "--- 워크스페이스 ---"
check "워크스페이스" "test -d '$WORKDIR'"
check "Getdesign.md" "test -f '$WORKDIR'/Getdesign.md"
check "harness-ops 스킬" "test -f '$WORKDIR'/skills/harness-ops/SKILL.md"
check "content-orchestration 스킬" "test -f '$WORKDIR'/skills/content-orchestration/SKILL.md"
check "content-pipeline 스킬" "grep -qE 'version: 1\\.(2|3)\\.0' '$WORKDIR'/skills/content-pipeline/SKILL.md"
check "marketing-research 스킬" "grep -qE 'version: 1\\.(1|2)\\.0' '$WORKDIR'/skills/marketing-research/SKILL.md"
check "channels/linkedin 스킬" "test -f '$WORKDIR'/skills/channels/linkedin/SKILL.md"
check "channels/newsletter 스킬" "test -f '$WORKDIR'/skills/channels/newsletter/SKILL.md"
check "content-orchestration config" "test -f '$WORKDIR'/config/content-orchestration.yaml"
check "content-studio-slides 스킬" "grep -q 'version: 1.1.0' '$WORKDIR'/skills/content-studio-slides/SKILL.md"
check "telegram-commander 스킬" "test -f '$WORKDIR'/skills/telegram-commander/SKILL.md"
check "notion-archive 스킬" "test -f '$WORKDIR'/skills/notion-archive/SKILL.md"
check "vibe-coding-cursor 스킬" "grep -q 'version: 1.1.0' '$WORKDIR'/skills/vibe-coding-cursor/SKILL.md"
check "playmcp-commander 스킬" "grep -q 'version: 1.1.0' '$WORKDIR'/skills/playmcp-commander/SKILL.md"
warn "PlayMCP MCP" "hermes mcp list 2>/dev/null | grep -E 'playmcp.*enabled'"
warn "mcporter CLI" "test -x $HOME/.hermes/node/bin/mcporter"
warn "mcporter mcp-gateway" "test -f $HOME/.mcporter/mcporter.json && grep -q mcp-gateway $HOME/.mcporter/mcporter.json"
check "hermes-run 스크립트" "test -x '$WORKDIR'/scripts/hermes-run.sh"
check "watch-telegram" "test -x '$WORKDIR'/scripts/watch-telegram.sh"
check "archive-to-notion" "test -x '$WORKDIR'/scripts/archive-to-notion.sh"
hermes_check "Notion OAuth" "$PY -c \"
import sys
sys.path.insert(0, '$WORKDIR/scripts')
from lib.notion_oauth import check_notion_oauth_status
s = check_notion_oauth_status()
raise SystemExit(0 if s.ok else 1)
\""
check "telegram-notify" "test -x '$WORKDIR'/scripts/telegram-notify.sh"
check "telegram-pipeline" "test -x '$WORKDIR'/scripts/telegram-pipeline.sh"
check "telegram-custom" "test -x '$WORKDIR'/scripts/telegram-custom.sh"
check "mail-digest.py" "test -f '$WORKDIR'/scripts/mail-digest.py"
check "personal-assistant 스킬" "test -f '$WORKDIR'/skills/personal-assistant/SKILL.md"
check "personal-tasks config" "test -f '$WORKDIR'/config/personal-tasks.yaml"
check "setup-telegram-routing" "test -x '$WORKDIR'/scripts/setup-telegram-routing.sh"
check "telegram-routing config" "test -f '$WORKDIR'/config/telegram-routing.yaml"
check "setup-slack-routing" "test -x '$WORKDIR'/scripts/setup-slack-routing.sh"
check "slack-routing config" "test -f '$WORKDIR'/config/slack-routing.yaml"
check "slack-notify" "test -x '$WORKDIR'/scripts/slack-notify.sh"
check "slack-daily-log" "test -x '$WORKDIR'/scripts/slack-daily-log.sh"
warn "Telegram quick_commands" "grep -q 'telegram-pipeline.sh qc pipeline' ~/.hermes/config.yaml"
warn "Slack free_response" "grep -q 'free_response_channels' ~/.hermes/config.yaml"
warn "Slack Bot Token" "grep -q '^SLACK_BOT_TOKEN=' ~/.hermes/.env"
check "telegram-post-sync" "test -x '$WORKDIR'/scripts/telegram-post-sync.sh"
check "polish-lecture-claude-design" "test -x '$WORKDIR'/scripts/polish-lecture-claude-design.sh"
check "lecture-design config" "test -f '$WORKDIR'/config/lecture-design.yaml"
check "run-research-brief" "test -x '$WORKDIR'/scripts/run-research-brief.sh"
check "run-content-package" "test -x '$WORKDIR'/scripts/run-content-package.sh"
check "run-newsletter" "test -x '$WORKDIR'/scripts/run-newsletter.sh"
check "newsletter-eval" "test -x '$WORKDIR'/scripts/newsletter-eval.sh"
check "newsletter config" "test -f '$WORKDIR'/config/newsletter.yaml"
check "newsletter_quality lib" "test -f '$WORKDIR'/scripts/lib/newsletter_quality.py"
check "newsletter_subject lib" "test -f '$WORKDIR'/scripts/lib/newsletter_subject.py"
check "newsletter_html lib" "test -f '$WORKDIR'/scripts/lib/newsletter_html.py"
check "email newsletter template" "test -f '$WORKDIR'/templates/email/newsletter.html"
check "update-studio" "test -x '$WORKDIR'/scripts/update-studio.sh"
check "lib/common.py" "test -f '$WORKDIR'/scripts/lib/common.py"
check "run-pipeline" "test -x '$WORKDIR'/scripts/run-pipeline.sh"
check "ddgs" "$PY -c 'import ddgs'"
check "setup-telegram 스크립트" "test -x '$WORKDIR'/scripts/setup-telegram.sh"
warn "Telegram Bot" "grep -q '^TELEGRAM_BOT_TOKEN=' ~/.hermes/.env"
warn "Discord 비활성" "! grep -q '^DISCORD_BOT_TOKEN=' ~/.hermes/.env"

echo ""
echo "--- 선택 통합 ---"
warn "Cursor Agent CLI" "test -x $HOME/.local/bin/cursor-agent"
warn "Cursor IDE CLI" "test -x $HOME/.local/bin/cursor || test -x /Applications/Cursor.app/Contents/Resources/app/bin/cursor || test -x /opt/homebrew/bin/cursor"
check "run-cursor-handoff" "test -x '$WORKDIR'/scripts/run-cursor-handoff.sh"
check "install-cursor-cli" "test -x '$WORKDIR'/scripts/install-cursor-cli.sh"
check "JARVIS.md" "test -f '$WORKDIR'/JARVIS.md"
check "jarvis-memory-eval" "test -x '$WORKDIR'/scripts/jarvis-memory-eval.sh"
check "mcp-easytool-eval" "test -x '$WORKDIR'/scripts/mcp-easytool-eval.sh"
check "pipeline-integrity-eval" "test -x '$WORKDIR'/scripts/pipeline-integrity-eval.sh"
warn "Node.js" "node --version"
warn "Python markitdown" "$PY -m markitdown --help"

echo ""
echo "--- Cron ---"
# pipefail + grep -q 조기 종료 시 hermes가 SIGPIPE로 실패 → 목록을 한 번만 캡처
CRON_LIST="$(hermes cron list 2>/dev/null || true)"
grep -E "weekly|research|content|lecture" <<<"$CRON_LIST" || echo "⚠️  주간 cron 미설정"
warn "Commander cron (morning)" "grep -q cron-morning-brief <<<\"\$CRON_LIST\""
warn "Commander cron (health)" "grep -q cron-health-alert <<<\"\$CRON_LIST\""
warn "Commander cron (notion oauth)" "grep -q cron-notion-oauth-watch <<<\"\$CRON_LIST\""

echo ""
echo "=== 결과: ✅ $PASS / ❌ $FAIL / ⚠️ $WARN ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
