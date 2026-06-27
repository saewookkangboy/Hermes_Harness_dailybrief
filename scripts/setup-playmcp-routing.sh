#!/usr/bin/env bash
# PlayMCP quick_commands — Telegram/Slack 동등 라우팅
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
ROUTING_YAML="$WORKDIR/config/playmcp-routing.yaml"
CONFIG="$HOME/.hermes/config.yaml"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

if [[ ! -f "$ROUTING_YAML" ]]; then
  echo "❌ $ROUTING_YAML 없음"
  exit 1
fi

chmod +x "$DIR/telegram-pipeline.sh" "$DIR/run-blog-pipeline.sh" 2>/dev/null || true

echo "=== PlayMCP 결정적 라우팅 설정 ==="

run_python() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

run_python - "$ROUTING_YAML" "$CONFIG" <<'PY'
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML 필요")
    sys.exit(1)

routing_path, config_path = sys.argv[1], sys.argv[2]
routing = yaml.safe_load(Path(routing_path).read_text(encoding="utf-8"))
config_path = Path(config_path)

if config_path.exists():
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
else:
    config = {}

qc = routing.get("quick_commands", {})
config["quick_commands"] = {**config.get("quick_commands", {}), **qc}
print(f"quick_commands: {len(qc)} commands merged")

playmcp_cfg = config.setdefault("playmcp", {})
prompt = routing.get("playmcp_routing", {}).get("channel_prompt", "")
if prompt:
    playmcp_cfg["channel_prompt"] = prompt.strip()
    print(f"playmcp channel_prompt: {len(prompt)} chars")

playmcp_cfg["enabled"] = True
config_path.write_text(
    yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False),
    encoding="utf-8",
)
print(f"✅ 저장: {config_path}")
PY

echo ""
echo "Gateway 재시작..."
hermes gateway restart 2>/dev/null || echo "⚠️  hermes gateway restart 수동 실행"
sleep 2
echo "=== PlayMCP 라우팅 완료 ==="
echo "검증: ./scripts/playmcp-integration-eval.sh"
