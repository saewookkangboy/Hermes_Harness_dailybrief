#!/usr/bin/env bash
# Hermes Content Studio — 헬스체크
set -euo pipefail

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

echo "=== Hermes Content Studio Health Check (Harness v1.2.0) ==="
echo "호스트: $(uname -m) / $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'unknown')"
echo ""

echo "--- Harness 5-Subsystem ---"
check "HARNESS.md" "test -f ~/hermes-content-studio/HARNESS.md"
check "harness.yaml" "test -f ~/hermes-content-studio/config/harness.yaml"
check "feature_list.json" "test -f ~/hermes-content-studio/.harness/feature_list.json"
check "progress.md" "test -f ~/hermes-content-studio/.harness/progress.md"
check "init.sh" "test -x ~/hermes-content-studio/scripts/init.sh"
check "harness-eval.sh" "test -x ~/hermes-content-studio/scripts/harness-eval.sh"
check "lib/harness.py" "test -f ~/hermes-content-studio/scripts/lib/harness.py"
check "studio v1.3.0" "grep -qE 'version: \"1\\.(2|3)\\.0\"' ~/hermes-content-studio/config/studio.yaml"

echo ""
echo "--- 핵심 서비스 ---"
check "Hermes CLI" "hermes --version"
check "Ollama 실행" "pgrep -x ollama"
check "Ollama API" "curl -sf http://127.0.0.1:11434/api/tags"
check "Hermes Gateway" "pgrep -f 'hermes_cli.main gateway'"
check "gemma4 모델" "ollama list 2>/dev/null | grep -q gemma4"
warn "Codex OAuth" "hermes auth status openai-codex 2>&1 | grep -q 'logged in'"
warn "Codex CLI" "test -x $HOME/.hermes/node/bin/codex"

echo ""
echo "--- 워크스페이스 ---"
check "워크스페이스" "test -d ~/hermes-content-studio"
check "Getdesign.md" "test -f ~/hermes-content-studio/Getdesign.md"
check "harness-ops 스킬" "test -f ~/hermes-content-studio/skills/harness-ops/SKILL.md"
check "content-orchestration 스킬" "test -f ~/hermes-content-studio/skills/content-orchestration/SKILL.md"
check "content-pipeline 스킬" "grep -qE 'version: 1\\.(2|3)\\.0' ~/hermes-content-studio/skills/content-pipeline/SKILL.md"
check "marketing-research 스킬" "grep -qE 'version: 1\\.(1|2)\\.0' ~/hermes-content-studio/skills/marketing-research/SKILL.md"
check "channels/linkedin 스킬" "test -f ~/hermes-content-studio/skills/channels/linkedin/SKILL.md"
check "channels/newsletter 스킬" "test -f ~/hermes-content-studio/skills/channels/newsletter/SKILL.md"
check "content-orchestration config" "test -f ~/hermes-content-studio/config/content-orchestration.yaml"
check "content-studio-slides 스킬" "grep -q 'version: 1.1.0' ~/hermes-content-studio/skills/content-studio-slides/SKILL.md"
check "telegram-commander 스킬" "test -f ~/hermes-content-studio/skills/telegram-commander/SKILL.md"
check "notion-archive 스킬" "test -f ~/hermes-content-studio/skills/notion-archive/SKILL.md"
check "vibe-coding-cursor 스킬" "grep -q 'version: 1.1.0' ~/hermes-content-studio/skills/vibe-coding-cursor/SKILL.md"
check "playmcp-commander 스킬" "grep -q 'version: 1.1.0' ~/hermes-content-studio/skills/playmcp-commander/SKILL.md"
warn "PlayMCP MCP" "hermes mcp list 2>/dev/null | grep -E 'playmcp.*enabled'"
warn "mcporter CLI" "test -x $HOME/.hermes/node/bin/mcporter"
warn "mcporter mcp-gateway" "test -f $HOME/.mcporter/mcporter.json && grep -q mcp-gateway $HOME/.mcporter/mcporter.json"
check "hermes-run 스크립트" "test -x ~/hermes-content-studio/scripts/hermes-run.sh"
check "watch-telegram" "test -x ~/hermes-content-studio/scripts/watch-telegram.sh"
check "archive-to-notion" "test -x ~/hermes-content-studio/scripts/archive-to-notion.sh"
check "Notion OAuth" "$HOME/.hermes/hermes-agent/venv/bin/python -c \"
import sys
sys.path.insert(0, '$HOME/hermes-content-studio/scripts')
from lib.notion_oauth import check_notion_oauth_status
s = check_notion_oauth_status()
raise SystemExit(0 if s.ok else 1)
\""
check "telegram-notify" "test -x ~/hermes-content-studio/scripts/telegram-notify.sh"
check "telegram-pipeline" "test -x ~/hermes-content-studio/scripts/telegram-pipeline.sh"
check "telegram-custom" "test -x ~/hermes-content-studio/scripts/telegram-custom.sh"
check "mail-digest.py" "test -f ~/hermes-content-studio/scripts/mail-digest.py"
check "personal-assistant 스킬" "test -f ~/hermes-content-studio/skills/personal-assistant/SKILL.md"
check "personal-tasks config" "test -f ~/hermes-content-studio/config/personal-tasks.yaml"
check "setup-telegram-routing" "test -x ~/hermes-content-studio/scripts/setup-telegram-routing.sh"
check "telegram-routing config" "test -f ~/hermes-content-studio/config/telegram-routing.yaml"
check "setup-slack-routing" "test -x ~/hermes-content-studio/scripts/setup-slack-routing.sh"
check "slack-routing config" "test -f ~/hermes-content-studio/config/slack-routing.yaml"
check "slack-notify" "test -x ~/hermes-content-studio/scripts/slack-notify.sh"
check "slack-daily-log" "test -x ~/hermes-content-studio/scripts/slack-daily-log.sh"
warn "Telegram quick_commands" "grep -q 'telegram-pipeline.sh qc pipeline' ~/.hermes/config.yaml"
warn "Slack free_response" "grep -q 'free_response_channels' ~/.hermes/config.yaml"
warn "Slack Bot Token" "grep -q '^SLACK_BOT_TOKEN=' ~/.hermes/.env"
check "telegram-post-sync" "test -x ~/hermes-content-studio/scripts/telegram-post-sync.sh"
check "polish-lecture-claude-design" "test -x ~/hermes-content-studio/scripts/polish-lecture-claude-design.sh"
check "lecture-design config" "test -f ~/hermes-content-studio/config/lecture-design.yaml"
check "run-research-brief" "test -x ~/hermes-content-studio/scripts/run-research-brief.sh"
check "run-content-package" "test -x ~/hermes-content-studio/scripts/run-content-package.sh"
check "run-newsletter" "test -x ~/hermes-content-studio/scripts/run-newsletter.sh"
check "newsletter-eval" "test -x ~/hermes-content-studio/scripts/newsletter-eval.sh"
check "newsletter config" "test -f ~/hermes-content-studio/config/newsletter.yaml"
check "newsletter_quality lib" "test -f ~/hermes-content-studio/scripts/lib/newsletter_quality.py"
check "newsletter_subject lib" "test -f ~/hermes-content-studio/scripts/lib/newsletter_subject.py"
check "newsletter_html lib" "test -f ~/hermes-content-studio/scripts/lib/newsletter_html.py"
check "email newsletter template" "test -f ~/hermes-content-studio/templates/email/newsletter.html"
check "update-studio" "test -x ~/hermes-content-studio/scripts/update-studio.sh"
check "lib/common.py" "test -f ~/hermes-content-studio/scripts/lib/common.py"
check "run-pipeline" "test -x ~/hermes-content-studio/scripts/run-pipeline.sh"
check "ddgs (Hermes venv)" "$HOME/.hermes/hermes-agent/venv/bin/python -c 'import ddgs'"
check "setup-telegram 스크립트" "test -x ~/hermes-content-studio/scripts/setup-telegram.sh"
warn "Telegram Bot" "grep -q '^TELEGRAM_BOT_TOKEN=' ~/.hermes/.env"
warn "Discord 비활성" "! grep -q '^DISCORD_BOT_TOKEN=' ~/.hermes/.env"

echo ""
echo "--- 선택 통합 ---"
warn "Cursor Agent CLI" "test -x $HOME/.local/bin/cursor-agent"
warn "Cursor IDE CLI" "test -x $HOME/.local/bin/cursor || test -x /Applications/Cursor.app/Contents/Resources/app/bin/cursor"
check "run-cursor-handoff" "test -x ~/hermes-content-studio/scripts/run-cursor-handoff.sh"
check "install-cursor-cli" "test -x ~/hermes-content-studio/scripts/install-cursor-cli.sh"
check "JARVIS.md" "test -f ~/hermes-content-studio/JARVIS.md"
check "jarvis-memory-eval" "test -x ~/hermes-content-studio/scripts/jarvis-memory-eval.sh"
check "mcp-easytool-eval" "test -x ~/hermes-content-studio/scripts/mcp-easytool-eval.sh"
check "pipeline-integrity-eval" "test -x ~/hermes-content-studio/scripts/pipeline-integrity-eval.sh"
warn "Node.js" "node --version"
warn "Python markitdown" "python3 -m markitdown --help"

echo ""
echo "--- Cron ---"
hermes cron list 2>/dev/null | grep -E "weekly|research|content|lecture" || echo "⚠️  주간 cron 미설정"
warn "Commander cron (morning)" "hermes cron list 2>/dev/null | grep -q cron-morning-brief"
warn "Commander cron (health)" "hermes cron list 2>/dev/null | grep -q cron-health-alert"
warn "Commander cron (notion oauth)" "hermes cron list 2>/dev/null | grep -q cron-notion-oauth-watch"

echo ""
echo "=== 결과: ✅ $PASS / ❌ $FAIL / ⚠️ $WARN ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
