#!/usr/bin/env bash
# Hermes Content Studio — Telegram 결정적 라우팅 설정
# quick_commands + channel_prompts → ~/.hermes/config.yaml
#
# Usage:
#   ./setup-telegram-routing.sh
#   TELEGRAM_ALLOWED_USERS=8975802496 ./setup-telegram-routing.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
ROUTING_YAML="$WORKDIR/config/telegram-routing.yaml"
CONFIG="$HOME/.hermes/config.yaml"
ENV_FILE="$HOME/.hermes/.env"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"

if [[ ! -f "$ROUTING_YAML" ]]; then
  echo "❌ $ROUTING_YAML 없음"
  exit 1
fi

# chat id for channel_prompts
CHAT_ID="${TELEGRAM_CHAT_ID:-}"
if [[ -z "$CHAT_ID" && -f "$ENV_FILE" ]]; then
  CHAT_ID=$(grep -E '^TELEGRAM_CHAT_ID=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
fi
if [[ -z "$CHAT_ID" && -f "$ENV_FILE" ]]; then
  CHAT_ID=$(grep -E '^TELEGRAM_ALLOWED_USERS=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
fi
if [[ -z "$CHAT_ID" ]]; then
  CHAT_ID="${TELEGRAM_ALLOWED_USERS:-}"
fi
if [[ -z "$CHAT_ID" ]]; then
  echo "⚠️  TELEGRAM_CHAT_ID/ALLOWED_USERS 없음 — channel_prompts 스킵"
  echo "   quick_commands만 적용됩니다."
fi

chmod +x "$DIR/telegram-pipeline.sh" 2>/dev/null || true

echo "=== Telegram 결정적 라우팅 설정 ==="

run_python() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

run_python - "$ROUTING_YAML" "$CONFIG" "$CHAT_ID" "${HERMES_EASYTOOL:-1}" <<'PY'
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML 필요: pip install pyyaml")
    sys.exit(1)

routing_path, config_path, chat_id, easytool_flag = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
routing = yaml.safe_load(Path(routing_path).read_text(encoding="utf-8"))
config_path = Path(config_path)
use_easytool = easytool_flag not in ("0", "false", "False")

if config_path.exists():
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
else:
    config = {}

# quick_commands 병합
qc = routing.get("quick_commands", {})
config["quick_commands"] = {**config.get("quick_commands", {}), **qc}
print(f"[1/2] quick_commands: {', '.join(qc.keys())}")

# channel_prompts (DM)
if chat_id:
    prompt = routing.get("telegram_routing", {}).get("channel_prompt", "")
    if use_easytool:
        sys.path.insert(0, str(Path(routing_path).resolve().parent.parent / "scripts"))
        try:
            from lib.easytool_prompt import build_compact_channel_prompt

            compact = build_compact_channel_prompt()
            if compact:
                prompt = compact
                print(f"[easytool] compact prompt: {len(prompt)} chars")
        except Exception as exc:
            print(f"[easytool] fallback verbose: {exc}")
    if prompt:
        tg = config.setdefault("telegram", {})
        cp = tg.setdefault("channel_prompts", {})
        cp[str(chat_id)] = prompt.strip()
        print(f"[2/2] channel_prompts: chat {chat_id} ({len(prompt)} chars)")
else:
    print("[2/2] channel_prompts: skipped (no chat id)")

config_path.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False), encoding="utf-8")
print(f"✅ 저장: {config_path}")
PY

echo ""
echo "[3/3] Gateway 재시작..."
hermes gateway restart
sleep 3

echo ""
echo "=== 완료 ==="
echo "Telegram 명령 (LLM 없음, 즉시 실행):"
echo "  /pipeline  — 리서치 + 콘텐츠 (~10s)"
echo "  /research  — 리서치 브리프"
echo "  /content   — 콘텐츠 패키지"
echo "  /sync           — Notion Permalink (백그라운드)"
echo "  /studio         — 로컬 상태 확인"
echo "  /notion-status  — Notion 아카이브 점검"
echo "  /notion-fix     — 중복 페이지 Draft Archive 이동"
echo "  /newsletter     — B2B 뉴스레터 생성"
echo ""
echo "Intent pack (결정적, LLM 없음):"
echo "  /morning /catch-up /publish /pending /approve /linkedin /traces /handoff /graph /commands"
echo ""
echo "Cron (setup-cron.sh):"
echo "  평일 09:00 모닝 브리핑 · 10:00/18:00 헬스 알림"
echo ""
echo "개인화 (Codex, 백그라운드):"
echo "  /mail      — 이메일 확인·정리"
echo "  /personal  — 맞춤 리서치·분석"
echo "  /automate  — Codex 자동화"
echo ""
echo "강의 (/pipeline 제외):"
echo "  /lecture-studio <요구사항>  — Outline + HTML → Notion"
echo ""
echo "자연어: pipeline → telegram-pipeline.sh | lecture → telegram-lecture.sh"
