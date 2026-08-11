#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${HERMES_WORKDIR:-$(cd "$DIR/.." && pwd)}"
MODE="${1:---unit}"
ARG2="${2:-today}"
export PYTHONPATH="$DIR${PYTHONPATH:+:$PYTHONPATH}"
export HERMES_WORKDIR="$WORKDIR"
pass=0; fail=0
ok(){ echo "PASS: $*"; pass=$((pass+1)); }
bad(){ echo "FAIL: $*"; fail=$((fail+1)); }

resolve_date() {
  local d="${1:-today}"
  if [[ "$d" == "today" ]]; then
    date +%F
  else
    echo "$d"
  fi
}

run_unit() {
  python3 - <<'PY' && ok "unit build_daily_blog_md" || bad "unit build_daily_blog_md"
import os
import sys
sys.modules.pop("lib", None)
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
from lib.blog_daily_report import BODY_MAX_CHARS, body_char_count, build_daily_blog_md
from lib.content_quality import Insight

insights = [
    Insight(
        title="에이전트 통제권",
        summary="EU AI Act와 비상 정지 요구가 확산되고 있습니다.",
        marketer_view="권한 캡과 HITL을 먼저 설계해야 합니다.",
        channels="blog|linkedin",
        url="https://example.com/a",
        source_title="EU AI Act",
    ),
    Insight(
        title="에이전트 예산",
        summary="에이전트 전용 예산 한도가 주목받습니다.",
        marketer_view="최악의 손실액을 숫자로 고정하세요.",
        channels="blog|linkedin",
        url="https://example.com/b",
        source_title="Budget",
    ),
]
md = build_daily_blog_md("2026-08-11", "AI Agent 일일 요약입니다.", insights)
assert "[오늘의 AI 트렌드]" in md
assert "주요 트렌드" in md
assert "주목" in md and "기술" in md
assert "시사점" in md or "대책" in md
assert "한 줄 요약" in md
assert "https://example.com/a" in md
assert body_char_count(md) <= BODY_MAX_CHARS
assert BODY_MAX_CHARS == 3000
print("unit ok", body_char_count(md))
PY

  python3 - <<'PY' && ok "unit build_threads_md" || bad "unit build_threads_md"
import os
import sys
sys.modules.pop("lib", None)
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
from lib.blog_daily_report import build_threads_md
from lib.content_quality import Insight

insights = [
    Insight(
        title="에이전트 통제권",
        summary="EU AI Act와 비상 정지 요구가 확산되고 있습니다.",
        marketer_view="권한 캡과 HITL을 먼저 설계해야 합니다.",
        channels="blog|linkedin",
        url="https://example.com/a",
        source_title="EU AI Act",
    ),
    Insight(
        title="에이전트 예산",
        summary="에이전트 전용 예산 한도가 주목받습니다.",
        marketer_view="최악의 손실액을 숫자로 고정하세요.",
        channels="blog|linkedin",
        url="https://example.com/b",
        source_title="Budget",
    ),
    Insight(
        title="에이전트 워크플로",
        summary="승인 단계가 분리된 워크플로가 늘고 있습니다.",
        marketer_view="반복 업무와 검토 지점을 함께 정의하세요.",
        channels="blog|linkedin",
        url="https://example.com/c",
        source_title="Workflow",
    ),
]
th = build_threads_md("2026-08-11", "AI Agent 일일 요약입니다.", insights)
assert "[블로그 링크]" in th
assert "?" in th or "댓글" in th
assert len(th.splitlines()) >= 5
assert "핵심만 말하면" in th
assert 3 <= th.count("→") <= 5
print("threads unit ok", th.count("→"))
PY

  python3 - <<'PY' && ok "unit daily HTML omits empty FAQPage" || bad "unit daily HTML omits empty FAQPage"
import os
import sys
from pathlib import Path
sys.modules.pop("lib", None)
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import lib.common
lib.common.WORKDIR = Path(os.environ["HERMES_WORKDIR"])
from lib.blog_daily_report import build_daily_blog_html
from lib.content_quality import Insight

html = build_daily_blog_html(
    "2026-08-11",
    "AI Agent 일일 요약입니다.",
    [
        Insight(
            title="에이전트 통제권",
            summary="EU AI Act와 비상 정지 요구가 확산되고 있습니다.",
            marketer_view="권한 캡과 HITL을 먼저 설계해야 합니다.",
            channels="blog|linkedin",
            url="https://example.com/a",
            source_title="EU AI Act",
        )
    ],
)
assert "https://schema.org/FAQPage" not in html
assert "{{FAQ_BLOCK}}" not in html
print("daily HTML has no empty FAQPage")
PY

  python3 - <<'PY' && ok "integration content package delegates daily assemblers" || bad "integration content package delegates daily assemblers"
import os
import sys
import tempfile
from pathlib import Path

sys.modules.pop("lib", None)
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
from lib.content_quality import (
    Insight,
    build_blog_article_md,
    build_blog_html,
    build_notion_packages,
)

insights = [
    Insight(
        title="에이전트 통제권",
        summary="EU AI Act와 비상 정지 요구가 확산되고 있습니다.",
        marketer_view="권한 캡과 HITL을 먼저 설계해야 합니다.",
        channels="blog|linkedin",
        url="https://example.com/a",
        source_title="EU AI Act",
    ),
    Insight(
        title="에이전트 예산",
        summary="에이전트 전용 예산 한도가 주목받습니다.",
        marketer_view="최악의 손실액을 숫자로 고정하세요.",
        channels="blog|linkedin",
        url="https://example.com/b",
        source_title="Budget",
    ),
]
stamp = "2026-08-11"
summary = "AI Agent 일일 요약입니다."
assert "[오늘의 AI 트렌드]" in build_blog_article_md(stamp, summary, insights)
assert "[오늘의 AI 트렌드]" in build_blog_html(stamp, summary, insights)
with tempfile.TemporaryDirectory() as tmp:
    paths = build_notion_packages(stamp, "brief", summary, insights, Path(tmp))
    assert "threads" in paths
    assert paths["threads"].name == f"{stamp}_threads.md"
    assert "[블로그 링크]" in paths["threads"].read_text(encoding="utf-8")
print("integration ok")
PY
}

run_live() {
  local DATE
  DATE="$(resolve_date "$1")"
  local BLOG="$WORKDIR/content/packages/${DATE}_blog-article.md"
  local THREADS="$WORKDIR/content/packages/${DATE}_threads.md"

  echo "=== blog-daily-report-eval --live $DATE ==="

  if [[ ! -f "$BLOG" ]]; then
    bad "live blog-article missing: $BLOG"
  else
    ok "live blog-article exists: $BLOG"
    if "$DIR/validate-output.sh" blog-article "$BLOG"; then
      ok "validate blog-article"
    else
      bad "validate blog-article"
    fi
    python3 - <<PY && ok "live body_char_count <= 3000" || bad "live body_char_count"
import sys
sys.path.insert(0, "$DIR")
from pathlib import Path
from lib.blog_daily_report import BODY_MAX_CHARS, body_char_count

text = Path("$BLOG").read_text(encoding="utf-8")
count = body_char_count(text)
if count > BODY_MAX_CHARS:
    raise SystemExit(f"body {count} > {BODY_MAX_CHARS}")
print(count)
PY
  fi

  if [[ ! -f "$THREADS" ]]; then
    bad "live threads missing: $THREADS"
  else
    ok "live threads exists: $THREADS"
    if "$DIR/validate-output.sh" threads-package "$THREADS"; then
      ok "validate threads-package"
    else
      bad "validate threads-package"
    fi
  fi
}

case "$MODE" in
  --unit)
    run_unit
    ;;
  --live)
    run_live "$ARG2"
    ;;
  --all)
    run_unit
    run_live "$ARG2"
    ;;
  *)
    echo "Usage: $0 [--unit|--live [DATE]|--all [DATE]]" >&2
    echo "  DATE defaults to today" >&2
    exit 1
    ;;
esac

echo "pass=$pass fail=$fail"
[[ "$fail" -eq 0 ]]
