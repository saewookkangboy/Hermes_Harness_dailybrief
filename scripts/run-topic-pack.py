#!/usr/bin/env python3
"""Topic Pack (M1–M6) — 임의 키워드 → 리서치 · AX Blueprint · Resource Map · Future Ahead · 채널 · 아카이브.

Usage:
  run-topic-pack.py "숏폼 커머스"
  run-topic-pack.py "RAG 평가" --date 2026-10-02 --stages M1,M2,M3,M4
  run-topic-pack.py "숏폼 커머스" --fixture tests/fixtures/topic/short-form-commerce.json
  run-topic-pack.py "CDP 도입 방법" --notion --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from lib.ax.pipeline import STAGES, run_topic_pack  # noqa: E402
from lib.common import studio_today  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Topic-Agnostic AX Topic Pack (M1–M6)")
    parser.add_argument("keyword", nargs="+", help="임의 키워드 (공백 포함 가능)")
    parser.add_argument("--date", default=studio_today())
    parser.add_argument("--stages", default=",".join(STAGES), help="예: M1,M2,M3,M4")
    parser.add_argument("--fixture", type=Path, help="오프라인 fixture JSON (네트워크 없이 결정적 실행)")
    parser.add_argument("--notion", action="store_true", help="M6에서 archive-to-notion --force 실행")
    parser.add_argument("--json", action="store_true", help="결과 요약 JSON 출력")
    args = parser.parse_args()

    stages = tuple(s.strip().upper() for s in args.stages.split(",") if s.strip())
    unknown = [s for s in stages if s not in STAGES]
    if unknown:
        parser.error(f"unknown stages: {unknown}")

    result = run_topic_pack(" ".join(args.keyword), args.date, stages=stages, fixture=args.fixture, notion=args.notion)
    summary = result.summary()
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        mark = "✅" if result.passed else "❌"
        print(f"{mark} Topic Pack: {summary['keyword']} ({summary['domain']} · {summary['intent']}) — {summary['total_seconds']}s")
        print(f"   게이트: {summary['gates']}")
        if result.stopped_at:
            print(f"   중단: {result.stopped_at} 게이트 미달 — 다운스트림 생략")
        for key, path in summary["paths"].items():
            print(f"   📄 {key}: {path}")
        if result.notion:
            print(f"   🔗 Notion: {result.notion.get('permalink') or result.notion}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
