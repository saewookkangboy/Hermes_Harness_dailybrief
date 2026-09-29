#!/usr/bin/env python3
"""캠페인 런칭 그래프 CLI — 브리프(YAML) → 카피 → 검수 → 사람 승인 → 런칭 패키지.

광고 계정에는 아무것도 쓰지 않습니다. 설정: config/campaign-launch.yaml

  python3 scripts/campaign-launch.py new ax-webinar-oct          # 브리프 템플릿 복사
  python3 scripts/campaign-launch.py run ax-webinar-oct --mode codex
  python3 scripts/campaign-launch.py status [id]
  python3 scripts/campaign-launch.py approve ax-webinar-oct [1 3]   # = 텔레그램·슬랙 "캠페인 승인 <id>"
  python3 scripts/campaign-launch.py reject ax-webinar-oct 사유
  python3 scripts/campaign-launch.py repackage ax-webinar-oct       # 열 이름 수정 후 패키지만 다시
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import campaign_graph as CG  # noqa: E402


def _today(s: str) -> date:
    return date.fromisoformat(s) if s else date.today()


def main() -> int:
    ap = argparse.ArgumentParser(description="Campaign launch graph (HITL · 광고 계정 쓰기 없음)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="브리프 템플릿을 content/campaigns/briefs/<id>.yaml 로 복사")
    p.add_argument("id")

    p = sub.add_parser("run", help="브리프 → 승인 카드까지 실행")
    p.add_argument("brief", help="브리프 경로 또는 id (content/campaigns/briefs/<id>.yaml)")
    p.add_argument("--mode", choices=list(CG.GENERATORS), default=None)
    p.add_argument("--restart", action="store_true", help="이미 승인·패키지된 id를 처음부터 다시")
    p.add_argument("--today", default="", help="YYYY-MM-DD (검증용)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--notify", dest="notify", action="store_true", default=None)
    g.add_argument("--no-notify", dest="notify", action="store_false")

    p = sub.add_parser("approve", help="승인 → 런칭 패키지")
    p.add_argument("id")
    p.add_argument("picks", nargs="*", type=int, help="승인할 변형 번호 (생략하면 전부)")
    p.add_argument("--by", default="cli")
    p.add_argument("--today", default="")

    p = sub.add_parser("reject", help="반려")
    p.add_argument("id")
    p.add_argument("reason", nargs="*")

    p = sub.add_parser("repackage", help="같은 승인본으로 패키지만 다시 만들기")
    p.add_argument("id")
    p.add_argument("--today", default="")

    p = sub.add_parser("status", help="캠페인 목록·상태")
    p.add_argument("id", nargs="?")
    p.add_argument("--card", action="store_true", help="승인 카드 다시 출력")

    args = ap.parse_args()
    cfg = CG.load_config()
    try:
        if args.cmd == "new":
            dest = CG.workdir() / cfg["briefs_dir"] / f"{args.id}.yaml"
            if dest.exists():
                raise CG.CampaignError(f"이미 있어요: {dest}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(CG.brief_template(args.id), encoding="utf-8")
            print(f"✅ 브리프 → {dest}\n채운 뒤: python3 scripts/campaign-launch.py run {args.id} --mode codex")
        elif args.cmd == "run":
            st = CG.start_campaign(
                args.brief, cfg=cfg, mode=args.mode, today=_today(args.today),
                notify_override=args.notify, restart=args.restart,
            )
            print(" → ".join(st["paths"][-1]))
            if st["status"] == "awaiting_approval":
                print("\n" + CG.format_approval_card(st, cfg))
            else:
                print(CG.format_status(st))
                return 1
        elif args.cmd == "approve":
            st = CG.approve(args.id, args.picks, cfg=cfg, by=args.by, today=_today(args.today))
            print(f"✅ 승인 · 패키지 → {st['package']['launch']}\n   CSV → {st['package']['csv']}")
        elif args.cmd == "reject":
            st = CG.reject(args.id, " ".join(args.reason) or "(사유 없음)", cfg=cfg)
            print(f"↩️ 반려 · {st['id']} — 브리프를 고친 뒤 run 으로 다시 돌리세요")
        elif args.cmd == "repackage":
            st = CG.repackage(args.id, cfg=cfg, today=_today(args.today))
            print(f"✅ 다시 만듦 → {st['package']['launch']}\n   CSV → {st['package']['csv']}")
        elif args.cmd == "status":
            if args.id:
                st = CG.load_state(cfg, args.id)
                print(CG.format_approval_card(st, cfg) if args.card and st.get("approval") else CG.format_status(st))
            else:
                print(CG.format_list(cfg))
    except CG.CampaignError as e:
        print(f"⚠️ {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
