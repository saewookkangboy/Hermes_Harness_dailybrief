"""Brief SoT — 일일 리서치 선행·신선도 게이트 (M2 진입 전)."""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
RESEARCH_DIR = WORKDIR / "content" / "research"
INSIGHT_LIMIT = 7


def brief_path(stamp: str) -> Path:
    return RESEARCH_DIR / f"{stamp}_brief.md"


def search_context_path(stamp: str) -> Path:
    return RESEARCH_DIR / f"_search_context_{stamp}.json"


def load_search_context(stamp: str) -> dict | None:
    path = search_context_path(stamp)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def brief_insight_count(stamp: str) -> int:
    path = brief_path(stamp)
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"^### \d+\.", text, re.M))


def needs_daily_research(stamp: str, *, force: bool = False) -> bool:
    """True → run-research-brief.sh 선행 필요."""
    if force:
        return True
    ctx = search_context_path(stamp)
    brief = brief_path(stamp)
    if not ctx.exists() or not brief.exists():
        return True
    payload = load_search_context(stamp)
    if not payload or payload.get("date") != stamp:
        return True
    if brief_insight_count(stamp) < INSIGHT_LIMIT:
        return True
    if payload.get("count", 0) < 7:
        return True
    return False


def assert_brief_ready_for_content(stamp: str) -> None:
    """M2 assemble 전 Brief SoT 검증 — 실패 시 SystemExit."""
    brief = brief_path(stamp)
    if not brief.exists():
        raise SystemExit(
            f"Brief SoT 없음: {brief}\n"
            f"먼저 실행: scripts/run-research-brief.sh {stamp}"
        )
    ctx = load_search_context(stamp)
    if not ctx:
        raise SystemExit(f"검색 컨텍스트 없음: {search_context_path(stamp)}")
    if ctx.get("date") != stamp:
        raise SystemExit(f"검색 컨텍스트 날짜 불일치: {ctx.get('date')} != {stamp}")
    n = brief_insight_count(stamp)
    if n < INSIGHT_LIMIT:
        raise SystemExit(f"Brief Top {INSIGHT_LIMIT} 미달: {n}개 — 리서치 재실행 필요")
    if not re.search(r"## Executive Summary", brief.read_text(encoding="utf-8")):
        raise SystemExit("Brief Executive Summary 없음")


def stamp_from_argv(default: str | None = None) -> str:
    if len(sys.argv) > 1 and sys.argv[1]:
        return sys.argv[1]
    if default:
        return default
    return date.today().isoformat()
