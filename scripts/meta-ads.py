#!/usr/bin/env python3
"""Meta Ads loop CLI — 피로도 감시 / 주간 리포트 (조회 전용, LLM 0회).

  python3 scripts/meta-ads.py fatigue            # 알림 텍스트 (0건이면 빈 출력)
  python3 scripts/meta-ads.py weekly             # 주간 리포트 저장 + 한 줄 요약
  python3 scripts/meta-ads.py weekly --mode sample --print-report

stdout 은 cron --deliver 로 Slack 에 그대로 게시됩니다. 파일은 content/ads/ 에 저장
(sample 모드는 _sample_ 접두사 → Notion 아카이브 제외).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import meta_ads as M  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["fatigue", "weekly"])
    ap.add_argument("--mode", choices=["sample", "api"])
    ap.add_argument("--date", help="파일명 날짜 (기본: 오늘 KST)")
    ap.add_argument("--print-report", action="store_true", help="저장한 리포트 전문도 출력")
    ap.add_argument("--require-api", action="store_true",
                    help="cron 전용: mode 가 api 가 아니면 아무것도 게시하지 않고 종료")
    args = ap.parse_args()

    try:
        cfg = M.load_config()
    except M.ConfigError as exc:
        print(f"⚠️ Meta 설정 오류 — 아무것도 조회·변경하지 않았습니다: {exc}")
        return 2
    if args.mode:
        cfg["mode"] = args.mode
    if args.require_api and cfg["mode"] != "api":
        # stdout 은 cron --deliver 로 Slack 에 게시되므로 비워 둠 (샘플 수치 게시 방지)
        print(f"meta-ads: mode={cfg['mode']} — cron 실행 건너뜀 (setup-meta-ads-cron.sh 를 다시 실행하세요)", file=sys.stderr)
        return 0
    try:
        ins = M.load_insights(cfg)
    except M.MetaApiError as exc:
        print(f"⚠️ Meta 인사이트 조회 실패 — 아무것도 변경하지 않았습니다: {exc}")
        return 2

    rows = M.evaluate_fatigue(ins, cfg)
    path = M.output_path(args.kind, ins, cfg, args.date)
    path.parent.mkdir(parents=True, exist_ok=True)

    if args.kind == "fatigue":
        alert = M.format_fatigue_alert(ins, rows, cfg)
        body = alert or f"피로도 교체 검토 대상 없음\n\n{M.source_line(ins, cfg)}"
        path.write_text(body + "\n", encoding="utf-8")
        if alert:
            print(alert)
    else:
        report = M.format_weekly_report(ins, rows, cfg)
        path.write_text(report, encoding="utf-8")
        flagged = sum(1 for r in rows if r.fatigued)
        t = M.totals(ins.current)
        label = "[샘플] " if ins.source == "sample" else ""
        print(
            f"{label}[Meta 주간 리포트] {ins.current.since}~{ins.current.until} · "
            f"지출 {M._money(t['spend'], ins.currency)} · 전환 {t['conversions']:,.0f} · 교체 검토 {flagged}개 · {path.name}"
        )
        if args.print_report:
            print()
            print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
