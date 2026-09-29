#!/usr/bin/env python3
"""네이버 데이터랩 수요 레이더 CLI (결정적, LLM 0회).

  python3 scripts/demand-radar.py                    # 리포트 저장 + Slack 메시지 출력
  python3 scripts/demand-radar.py --mode sample --print-report

stdout 은 cron --deliver 로 Slack 에 게시됩니다. 리포트: content/signals/{date}_demand-radar.md
(sample 모드는 _sample_ 접두사 → Notion 아카이브 제외). M1 병합은 사람이 /research 로 합니다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import demand_radar as R  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["sample", "api"])
    ap.add_argument("--date", help="파일명 날짜 (기본: 오늘 KST)")
    ap.add_argument("--print-report", action="store_true")
    ap.add_argument("--require-api", action="store_true",
                    help="cron 전용: mode 가 api 가 아니면 아무것도 게시하지 않고 종료")
    args = ap.parse_args()

    cfg = R.load_config()
    if args.mode:
        cfg["mode"] = args.mode
    if args.require_api and cfg["mode"] != "api":
        # stdout 은 cron --deliver 로 Slack 에 게시되므로 비워 둠 (샘플 수치 게시 방지)
        print(f"demand-radar: mode={cfg['mode']} — cron 실행 건너뜀 (setup-demand-radar-cron.sh 를 다시 실행하세요)", file=sys.stderr)
        return 0
    try:
        radar = R.build_radar(cfg)
    except R.DataLabError as exc:
        print(f"⚠️ 데이터랩 조회 실패: {exc}")
        return 2

    report = R.format_report(radar, cfg)
    path = R.output_path(radar, cfg, args.date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    print(R.format_slack(radar, cfg, path.name))
    if args.print_report:
        print()
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
