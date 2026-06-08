#!/usr/bin/env bash
# Commander 자연어 가이드 — Telegram + Slack 전송
set -euo pipefail

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
GUIDE="${1:-$HOME/hermes-content-studio/content/logs/2026-06-08_commander-natural-language-guide.md}"

if [[ ! -f "$GUIDE" ]]; then
  echo "❌ 가이드 없음: $GUIDE" >&2
  exit 1
fi

# shellcheck source=lib/commander_notify.sh
source "$SCRIPTS/lib/commander_notify.sh"
# shellcheck source=lib/slack_home.sh
source "$SCRIPTS/lib/slack_home.sh"

CHAT="$(commander_load_chat_id)"
SLACK="$(studio_slack_home_channel)"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
DIR="$SCRIPTS"

run_py() {
  if [[ -x "$HERMES_PY" ]]; then
    "$HERMES_PY" "$@"
  else
    python3 "$@"
  fi
}

echo "=== Commander 가이드 전송 ==="
echo "원본: $GUIDE"

run_py - "$GUIDE" "$CHAT" "$SLACK" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "hermes-content-studio" / "scripts"))

from lib.slack_notify import send_long_text
from lib.telegram_notify import send_message

guide_path, chat_id, slack_id = sys.argv[1], sys.argv[2], sys.argv[3]
raw = Path(guide_path).read_text(encoding="utf-8")
# YAML front 없음 — 첫 --- 이후 본문
parts = raw.split("---", 2)
body = parts[-1].strip() if len(parts) > 1 else raw.strip()

header = (
    "📘 Hermes Commander 가이드\n"
    "자연어 vs 슬래시 · Telegram · Slack\n\n"
)
text = header + body

tg_ok = slack_ok = True
if chat_id:
    if len(text) <= 3900:
        tg_ok = send_message(chat_id, text)
        print("✅ Telegram 1/1" if tg_ok else "❌ Telegram 실패")
    else:
        cut = text.rfind("\n## ", 0, 3600)
        if cut < 500:
            cut = 3600
        p1 = text[:cut].rstrip() + "\n\n… (2/2 계속)"
        p2 = "📘 가이드 (2/2)\n\n" + text[cut:].lstrip()
        tg_ok = send_message(chat_id, p1) and send_message(chat_id, p2)
        print("✅ Telegram 2파트" if tg_ok else "❌ Telegram 실패")
else:
    print("⚠️ TELEGRAM_CHAT_ID 없음 — 스킵")

if slack_id:
    slack_ok = send_long_text(slack_id, text)
    print(f"✅ Slack → {slack_id}" if slack_ok else "❌ Slack 실패")
else:
    print("⚠️ SLACK_HOME_CHANNEL 없음 — 스킵")

sys.exit(0 if (tg_ok and slack_ok) else 1)
PY

echo "=== 완료 ==="
