#!/usr/bin/env bash
# Hermes Content Studio — Slack 결정적 라우팅 설정
# quick_commands + slack.channel_prompts + free_response_channels → ~/.hermes/config.yaml
#
# Usage:
#   ./setup-slack-routing.sh
#   SLACK_HOME_CHANNEL=C0B8CN2EA05 ./setup-slack-routing.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
ROUTING_YAML="$WORKDIR/config/slack-routing.yaml"
CONFIG="$HOME/.hermes/config.yaml"
ENV_FILE="$HOME/.hermes/.env"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

if [[ ! -f "$ROUTING_YAML" ]]; then
  echo "❌ $ROUTING_YAML 없음"
  exit 1
fi

# Home channel for prompts + free-response slash commands
SLACK_CHANNEL="${SLACK_HOME_CHANNEL:-}"
if [[ -z "$SLACK_CHANNEL" && -f "$ENV_FILE" ]]; then
  SLACK_CHANNEL=$(grep -E '^SLACK_HOME_CHANNEL=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
fi
if [[ -z "$SLACK_CHANNEL" ]]; then
  SLACK_CHANNEL=$(grep -E 'default_home_channel:' "$ROUTING_YAML" 2>/dev/null | head -1 | awk '{print $2}' || true)
fi
if [[ -z "$SLACK_CHANNEL" ]]; then
  echo "⚠️  SLACK_HOME_CHANNEL 없음 — channel_prompts/free_response 스킵"
  echo "   quick_commands만 적용됩니다."
fi

chmod +x "$DIR/telegram-pipeline.sh" "$DIR/slack-notify.sh" 2>/dev/null || true

echo "=== Slack 결정적 라우팅 설정 ==="

run_python() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

run_python - "$ROUTING_YAML" "$CONFIG" "$SLACK_CHANNEL" <<'PY'
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML 필요: pip install pyyaml")
    sys.exit(1)

routing_path, config_path, channel_id = sys.argv[1], sys.argv[2], sys.argv[3]
routing = yaml.safe_load(Path(routing_path).read_text(encoding="utf-8"))
config_path = Path(config_path)

if config_path.exists():
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
else:
    config = {}

# quick_commands 병합 (Telegram과 동일 — 전역)
qc = routing.get("quick_commands", {})
config["quick_commands"] = {**config.get("quick_commands", {}), **qc}
print(f"[1/3] quick_commands: {', '.join(qc.keys())}")

slack_cfg = config.setdefault("slack", {})

if channel_id:
    prompt = routing.get("slack_routing", {}).get("channel_prompt", "")
    if prompt:
        cp = slack_cfg.setdefault("channel_prompts", {})
        cp[str(channel_id)] = prompt.strip()
        print(f"[2/3] channel_prompts: {channel_id} ({len(prompt)} chars)")

    # /pipeline 등 슬래시 커맨드 — @mention 없이 홈 채널에서 즉시 실행
    frc = slack_cfg.get("free_response_channels")
    if isinstance(frc, list):
        channels = {str(c) for c in frc}
    elif isinstance(frc, str) and frc.strip():
        channels = {c.strip() for c in frc.split(",") if c.strip()}
    else:
        channels = set()
    channels.add(str(channel_id))
    slack_cfg["free_response_channels"] = sorted(channels)
    print(f"[3/3] free_response_channels: {', '.join(slack_cfg['free_response_channels'])}")
else:
    print("[2/3] channel_prompts: skipped (no channel id)")
    print("[3/3] free_response_channels: skipped (no channel id)")

config_path.write_text(
    yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False),
    encoding="utf-8",
)
print(f"✅ 저장: {config_path}")
PY

echo ""
echo "[4/4] Gateway 재시작..."
hermes gateway restart
sleep 3

echo ""
echo "=== 완료 ==="
echo "Slack 명령 (LLM 없음, #일반데이터 등 홈 채널):"
echo "  /pipeline  — 리서치 + 콘텐츠 (~10s) + Notion sync-bg"
echo "  /research  — 리서치 브리프"
echo "  /content   — 콘텐츠 패키지"
echo "  /sync      — Notion Permalink"
echo "  /studio    — 로컬 상태 확인"
echo "  /notion-status — Notion 아카이브 점검"
echo ""
echo "사전 준비:"
echo "  1. ./setup-slack.sh — Bot Token + SLACK_HOME_CHANNEL"
echo "  2. Slack에서 @Hermes 봇을 #일반데이터에 /invite"
echo "  3. 홈 채널에서 /pipeline 입력 (free_response — @mention 불필요)"
