#!/usr/bin/env bash
# Hermes Agent · Harness · Telegram/Slack 커맨더 통합 점검
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$HOME/hermes-content-studio}"
REPORT="$WORKDIR/content/logs/$(studio_today 2>/dev/null || date +%Y-%m-%d)_commander-integration-eval.md"
mkdir -p "$WORKDIR/content/logs"
PASS=0; FAIL=0
record() { [[ "$1" == PASS ]] && PASS=$((PASS+1)) || FAIL=$((FAIL+1)); echo "$1 $2"; }

# shellcheck source=lib/studio-date.sh
source "$DIR/lib/studio-date.sh"
# shellcheck source=lib/telegram_sync_guard.sh
source "$DIR/lib/telegram_sync_guard.sh"

echo "=== Commander Integration Eval ==="

# 1) 날짜 SoT
CMD_DATE="$(studio_commander_date)"
[[ -n "$CMD_DATE" ]] && record PASS "studio_commander_date" || record FAIL "commander_date"
echo "$CMD_DATE" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' && record PASS "date_format" || record FAIL "date_format"

# 2) notify_format — 타 날짜 페이지 누출 방지
python3 <<PY && record PASS "pages_for_stamp_no_fallback" || record FAIL "pages_for_stamp"
import sys
sys.path.insert(0, "${DIR}")
from lib.notify_format import pages_for_stamp, format_completion
pages = [
    {"path": "/x/2026-06-05_blog.md", "title": "Blog — 2026-06-05", "label": "Blog", "icon": "📝", "url": "https://a"},
    {"path": "/x/2026-06-08_blog.md", "title": "Blog — 2026-06-08", "label": "Blog", "icon": "📝", "url": "https://b"},
]
f = pages_for_stamp(pages, "2026-06-08")
assert len(f) == 1 and "2026-06-08" in f[0]["path"]
empty = pages_for_stamp(pages, "2099-01-01")
assert empty == []
msg = format_completion("2026-06-08", pages)
assert "2026-06-05" not in msg or msg.count("2026-06-05") == 0
assert "2026-06-08" in msg
PY

# 3) notify dedupe
python3 <<PY && record PASS "notify_dedupe" || record FAIL "notify_dedupe"
import sys
sys.path.insert(0, "${DIR}")
from lib.notify_dedupe import should_skip_notify
c = "test-chat"
t = "same-body"
assert not should_skip_notify(c, t, stamp="2026-06-08")
assert should_skip_notify(c, t, stamp="2026-06-08")
assert not should_skip_notify(c, t + "!", stamp="2026-06-08")
PY

# 4) telegram sync guard
telegram_sync_begin "2026-06-08-test"
telegram_sync_should_skip_watch && record PASS "sync_guard_lock" || record FAIL "sync_guard"
telegram_sync_begin "2026-06-05-test"
grep -q "2026-06-08-test" "$WORKDIR/.harness/telegram-sync.lock" 2>/dev/null \
  && record PASS "sync_guard_no_downgrade" || record FAIL "sync_guard_downgrade"
telegram_sync_end
telegram_sync_should_skip_watch && record FAIL "sync_guard_clear" || record PASS "sync_guard_clear"

# 4b) archive date clamp (Telegram 경로)
grep -q 'REQUESTED_DATE' "$DIR/archive-to-notion.sh" && record PASS "archive_requested_date" || record FAIL "archive_date_parse"
grep -q 'commander SoT' "$DIR/archive-to-notion.sh" && record PASS "archive_date_clamp" || record FAIL "archive_clamp"
grep -q 'flock' "$DIR/archive-to-notion.sh" && record PASS "archive_flock" || record FAIL "archive_flock"
grep -q 'HERMES_WATCH_POST_SYNC' "$DIR/watch-telegram.sh" && record PASS "watch_post_sync_default_off" || record FAIL "watch_post_sync"
[[ -x "$DIR/kill-stale-watch-telegram.sh" ]] && record PASS "kill_stale_watch" || record FAIL "kill_stale_watch"

# 5) 스크립트·설정 존재
for f in telegram-pipeline.sh watch-telegram.sh telegram-post-sync.sh hermes-agent.sh \
  archive-to-notion.sh harness-eval.sh health-check.sh; do
  [[ -x "$DIR/$f" || -f "$DIR/$f" ]] && record PASS "script_$f" || record FAIL "script_$f"
done

# 6) telegram routing quick_commands
grep -q 'telegram-pipeline.sh qc pipeline' "$WORKDIR/config/telegram-routing.yaml" \
  && record PASS "routing_pipeline" || record FAIL "routing"
grep -q 'telegram-pipeline.sh qc sync' "$WORKDIR/config/telegram-routing.yaml" \
  && record PASS "routing_sync" || record FAIL "routing_sync"
grep -q 'qc morning' "$WORKDIR/config/telegram-routing.yaml" \
  && record PASS "routing_morning" || record FAIL "routing_morning"
grep -q 'qc newsletter' "$WORKDIR/config/telegram-routing.yaml" \
  && record PASS "routing_newsletter" || record FAIL "routing_newsletter"
"$DIR/telegram-pipeline.sh" qc morning 2>/dev/null | grep -qi 'Morning Pack' \
  && record PASS "qc_morning_exec" || record FAIL "qc_morning_exec"

# 7) newsletter paste 배포 (ESP 없음)
grep -q 'esp_send: false' "$WORKDIR/config/newsletter.yaml" \
  && record PASS "no_esp_send" || record FAIL "esp"
[[ -f "$WORKDIR/content/packages/${CMD_DATE}_newsletter-paste.md" ]] \
  && record PASS "paste_pack_exists" || record FAIL "paste_pack"

# 8) harness regression (quick)
"$DIR/harness-eval.sh" --quick >/dev/null 2>&1 && record PASS "harness_eval_quick" || record FAIL "harness_eval"

# 9) archive python syntax
python3 -m py_compile "$DIR/archive-to-notion.py" && record PASS "archive_py_compile" || record FAIL "archive_py"

{
  echo "# Commander Integration Eval"
  echo ""
  echo "PASS: **$PASS** · FAIL: **$FAIL**"
  echo ""
  echo "## 점검 범위"
  echo "- studio_commander_date · pages_for_stamp · notify dedupe"
  echo "- telegram_sync_guard · routing · newsletter paste"
  echo "- harness-eval --quick"
  echo ""
  echo "## commander_date"
  echo "- \`$CMD_DATE\`"
  echo ""
  echo "## Telegram 슬래시 Notion sync"
  echo "- 파이프라인: \`--notify-final\` 1회 · \`telegram_sync_begin\`"
  echo "- watch-telegram: post-sync 기본 OFF · 슬래시 시 skip · 단일 인스턴스 lock"
  echo "- archive-to-notion: flock + commander 날짜 보정 (Telegram/notify-final)"
} > "$REPORT"

echo "Report: $REPORT"
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
