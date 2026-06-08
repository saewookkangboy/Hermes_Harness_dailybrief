#!/usr/bin/env python3
"""Hermes Conversational Agent — Phase 1–3 CLI (Memory · M4 · Graph · HITL · Registry)."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
SCRIPTS = WORKDIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib.common import studio_today  # noqa: E402
from lib.memory_router import brief_top3, recent_briefs, route_query  # noqa: E402
from lib.personal_bridge import format_inbox_summary, queue_topic_for_brief, sync_inbox_from_personal  # noqa: E402
from lib.proactive_triggers import format_proactive_block, run_proactive_checks  # noqa: E402
from lib.linkedin_pipeline import format_pipeline_summary, run_linkedin_pipeline  # noqa: E402
from lib.m4_analytics import format_m4_report, record_agent_trace, save_m4_snapshot  # noqa: E402
from lib.session_handoff import format_resume_block, write_session_handoff  # noqa: E402
from lib.brief_graph import (  # noqa: E402
    format_graph_summary,
    patch_unified_context,
    save_brief_graph,
)
from lib.command_registry import (  # noqa: E402
    format_registry_table,
    list_commands,
    list_intents,
    run_script_command,
)
from lib.publish_gate import (  # noqa: E402
    approve_channels,
    execute_approved_publish,
    format_approval_card,
    format_pending_status,
    format_telegram_approval,
    request_publish,
)
from lib.brief_gate import brief_path  # noqa: E402
from lib.content_quality import parse_brief  # noqa: E402
from lib.newsletter_quality import assemble_newsletter, build_newsletter_md  # noqa: E402
from lib.session_sot import load_session, record_action, resume_hint  # noqa: E402

INTENT_ALIASES: dict[str, list[str]] = {
    "morning": ["/morning", "모닝", "아침", "morning"],
    "catch-up": ["/catch-up", "/catchup", "catch-up", "catchup", "최근 요약", "이번 주"],
    "publish": ["/publish", "발행", "publish"],
    "deep": ["/deep", "심층", "deep"],
    "ask": ["/ask", "질문", "뭐였지", "찾아줘"],
    "linkedin": ["/linkedin", "링크드인 전략", "linkedin strategy"],
    "traces": ["/traces", "m4", "성능 리포트"],
    "handoff": ["/handoff", "핸드오프", "이어하기"],
    "graph": ["/graph", "brief graph", "브리프 그래프"],
    "approve": ["/approve", "승인", "approve"],
    "commands": ["/commands", "명령 목록", "registry"],
    "newsletter": ["/newsletter", "뉴스레터", "newsletter"],
}


def detect_intent(text: str) -> tuple[str, str]:
    """Return (intent_id, remainder args)."""
    t = text.strip()
    lower = t.lower()
    for intent, aliases in INTENT_ALIASES.items():
        for alias in aliases:
            if lower == alias.lower() or lower.startswith(alias.lower() + " "):
                rest = t[len(alias) :].strip()
                return intent, rest
    if re.search(r"[?？]|뭐였|찾아|알려", t):
        return "ask", t
    return "", t


def _commander_notify(msg: str) -> None:
    env = {**dict(__import__("os").environ)}
    subprocess.run(
        ["bash", str(SCRIPTS / "lib" / "commander_notify.sh"), "notify", msg],
        check=False,
        env=env,
        cwd=str(WORKDIR),
    )


def cmd_route(args: argparse.Namespace) -> int:
    stamp = args.date or studio_today()
    t0 = time.perf_counter()
    result = route_query(args.query, stamp)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    record_action(args.session, intent="ask", action="memory_route", stamp=stamp)
    print(result.answer)
    print(f"\n---\n⏱ {elapsed_ms:.1f}ms · hits={len(result.hits)} · skip_web={result.skip_web_search}")
    if args.json:
        print(json.dumps({**result.to_dict(), "elapsed_ms": elapsed_ms}, ensure_ascii=False, indent=2))
    return 0


def _trace_intent(args: argparse.Namespace, intent: str, action: str, t0: float, stamp: str = "") -> None:
    elapsed_ms = (time.perf_counter() - t0) * 1000
    record_agent_trace(intent, action, elapsed_ms, stamp=stamp or args.date or studio_today())


def cmd_morning(args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    stamp = args.date or studio_today()
    parts = [f"☀️ Morning Pack · {stamp}", ""]
    alerts = run_proactive_checks(stamp)
    parts.append(format_proactive_block(alerts))
    parts.append("")
    parts.append(brief_top3(stamp))
    resume = format_resume_block(args.session) or resume_hint(args.session)
    if resume:
        parts.extend(["", resume])
    record_action(args.session, intent="morning", action="morning_pack", stamp=stamp)
    _trace_intent(args, "morning", "morning_pack", t0, stamp)
    print("\n".join(parts))
    return 0


def cmd_catch_up(args: argparse.Namespace) -> int:
    days = args.days or 3
    parts = [recent_briefs(days), ""]
    stamp = args.date or studio_today()
    nr = route_query("notion permalink", stamp)
    if nr.hits:
        parts.append(nr.answer)
    record_action(args.session, intent="catch-up", action=f"recent_{days}d", stamp=stamp)
    print("\n".join(parts))
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    stamp = args.date or studio_today()
    channel = (args.channel or "linkedin").lower()
    if channel not in ("blog", "instagram", "linkedin"):
        print(f"❌ 채널: blog | instagram | linkedin (got {channel})", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"[dry-run] HERMES_SKIP_RESEARCH=1 run-content-package.sh {stamp}")
        print(f"[dry-run] validate {channel}")
        print(f"[dry-run] archive-to-notion.sh {stamp} --force --notify-final")
        return 0
    if not getattr(args, "approve", False):
        queue = request_publish(stamp, [channel])
        record_action(
            args.session,
            intent="publish",
            action=f"hitl_pending_{channel}",
            stamp=stamp,
            pending=[f"approve_{channel}"],
        )
        _trace_intent(args, "publish", "hitl_gate", t0, stamp)
        card = format_approval_card(stamp, queue)
        print(card)
        _commander_notify(format_telegram_approval(stamp, queue))
        return 0
    approve_channels(stamp, [channel])
    result = execute_approved_publish(stamp, [channel])
    record_action(args.session, intent="publish", action=f"publish_{channel}", stamp=stamp)
    _trace_intent(args, "publish", f"publish_{channel}", t0, stamp)
    msg = f"✅ publish {channel} · {stamp} · {result.get('published', [])}"
    print(msg)
    _commander_notify(msg)
    return 0


def cmd_deep(args: argparse.Namespace) -> int:
    topic = args.topic or args.query or ""
    if not topic:
        print("❌ 주제 필요: hermes-agent.py deep 'AX 트렌드'", file=sys.stderr)
        return 1
    stamp = args.date or studio_today()
    result = route_query(topic, stamp)
    sync_inbox_from_personal(stamp)
    queue_topic_for_brief(topic, source="deep-intent")
    parts = [
        f"🔍 Deep Pack · {stamp}",
        "",
        result.answer,
        "",
        format_inbox_summary(),
        "",
        "다음: telegram-custom.sh qc ask-bg \"{topic}\" 또는 run-research-brief.sh".format(topic=topic[:40]),
    ]
    record_action(
        args.session,
        intent="deep",
        action="deep_queue",
        stamp=stamp,
        pending=["research_followup"],
    )
    print("\n".join(parts))
    return 0


def cmd_proactive(args: argparse.Namespace) -> int:
    stamp = args.date or studio_today()
    alerts = run_proactive_checks(stamp)
    print(format_proactive_block(alerts))
    if args.json:
        print(json.dumps(alerts, ensure_ascii=False, indent=2))
    return 0


def cmd_bridge_sync(args: argparse.Namespace) -> int:
    stamp = args.date or studio_today()
    data = sync_inbox_from_personal(stamp)
    print(format_inbox_summary())
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_session(args: argparse.Namespace) -> int:
    if args.clear:
        record_action(args.session, intent="", action="cleared", stamp="", pending=[])
        print("session cleared")
        return 0
    s = load_session(args.session)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


def cmd_linkedin(args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    stamp = args.date or studio_today()
    try:
        result = run_linkedin_pipeline(stamp, validate=args.validate)
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    record_action(
        args.session,
        intent="linkedin",
        action="linkedin_m3_pipeline",
        stamp=stamp,
        pending=["notion_sync"] if not args.dry_run else [],
    )
    _trace_intent(args, "linkedin", "m3_pipeline", t0, stamp)
    print(format_pipeline_summary(result))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_traces(args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    days = args.days or 7
    report = format_m4_report(days)
    path = save_m4_snapshot(days)
    record_action(args.session, intent="traces", action="m4_report", stamp=args.date or studio_today())
    _trace_intent(args, "traces", "m4_report", t0)
    print(report)
    print(f"\n---\nsnapshot: {path}")
    if args.json:
        from lib.m4_analytics import build_m4_report

        print(json.dumps(build_m4_report(days), ensure_ascii=False, indent=2))
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    days = args.days or 14
    path = save_brief_graph(days)
    stamp = args.date or studio_today()
    record_action(args.session, intent="graph", action="build_graph", stamp=stamp)
    _trace_intent(args, "graph", "build_graph", t0, stamp)
    print(format_graph_summary(days))
    print(f"\n---\ngraph: {path}")
    if args.write_unified:
        patched = patch_unified_context(stamp, days)
        if patched:
            print(f"unified: {patched}")
    if args.json:
        from lib.brief_graph import load_brief_graph

        print(json.dumps(load_brief_graph(), ensure_ascii=False, indent=2))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    stamp = args.date or studio_today()
    channels = args.channels or ["all"]
    if isinstance(channels, str):
        channels = [channels]
    data = approve_channels(stamp, channels)
    result = execute_approved_publish(stamp, data.get("approved_channels"))
    record_action(
        args.session,
        intent="approve",
        action=f"approve_{','.join(channels)}",
        stamp=stamp,
        pending=[],
    )
    _trace_intent(args, "approve", "hitl_execute", t0, stamp)
    print(format_approval_card(stamp, data))
    msg = f"✅ HITL 발행 완료 · {stamp} · {result.get('published', [])}"
    print(f"\n{msg}")
    _commander_notify(msg)
    return 0


def cmd_pending(args: argparse.Namespace) -> int:
    stamp = args.date or ""
    print(format_pending_status(stamp or None))
    return 0


def cmd_commands(args: argparse.Namespace) -> int:
    print(format_registry_table())
    if args.json:
        print(
            json.dumps(
                {"intents": list_intents(), "commands": list_commands()},
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    stamp = args.date or studio_today()
    try:
        rc = run_script_command(args.command_id, stamp, args.extra or [])
    except (KeyError, ValueError) as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    record_action(args.session, intent="run", action=args.command_id, stamp=stamp)
    return rc


def cmd_newsletter(args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    stamp = args.date or studio_today()
    path = brief_path(stamp)
    if not path.exists():
        print(f"❌ Brief 없음: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    nl_path, ctx_path, html_path, paste_path = assemble_newsletter(stamp, text)
    scores_path = WORKDIR / "content" / "newsletter" / f"{stamp}_newsletter_subject-scores.json"
    record_action(args.session, intent="newsletter", action="assemble_newsletter", stamp=stamp)
    _trace_intent(args, "newsletter", "assemble", t0, stamp)
    if args.validate:
        subprocess.run([str(SCRIPTS / "validate-output.sh"), "newsletter", str(nl_path)], check=False)
        subprocess.run([str(SCRIPTS / "validate-output.sh"), "newsletter-context", str(ctx_path)], check=False)
        subprocess.run([str(SCRIPTS / "validate-output.sh"), "newsletter-html", str(html_path)], check=False)
        subprocess.run([str(SCRIPTS / "validate-output.sh"), "newsletter-paste", str(paste_path)], check=False)
        if scores_path.exists():
            subprocess.run(
                [str(SCRIPTS / "validate-output.sh"), "newsletter-subject-scores", str(scores_path)],
                check=False,
            )
    summary, insights = parse_brief(text)
    preview = build_newsletter_md(stamp, summary, insights).split("## 30초 TLDR")[0]
    print(preview)
    print(f"\n---\n📄 {nl_path}\n📦 {ctx_path}\n📧 {html_path}\n📋 {paste_path}\n📊 {scores_path}")
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    path = write_session_handoff(args.session, m4_days=args.days or 7)
    record_action(args.session, intent="handoff", action="write_handoff", stamp=args.date or studio_today())
    _trace_intent(args, "handoff", "write_handoff", t0)
    print(f"✅ Session handoff → {path}")
    print("")
    print(format_resume_block(args.session))
    return 0


def _auto_defaults(args: argparse.Namespace, intent: str, rest: str) -> None:
    """auto 라우팅 시 서브커맨드 전용 인자 기본값."""
    defaults: dict[str, dict] = {
        "catch-up": {"days": 3},
        "publish": {"channel": rest.split()[0] if rest else "linkedin", "dry_run": False, "approve": False},
        "deep": {"topic": rest},
        "linkedin": {"validate": False, "dry_run": False},
        "traces": {"days": 7},
        "handoff": {"days": 7},
        "graph": {"days": 14, "write_unified": False},
        "approve": {"channels": rest.split() if rest else ["all"]},
    }
    for key, val in defaults.get(intent, {}).items():
        if not hasattr(args, key):
            setattr(args, key, val)


def cmd_auto(args: argparse.Namespace) -> int:
    intent, rest = detect_intent(args.text or "")
    args.query = rest
    _auto_defaults(args, intent, rest)
    if intent == "morning":
        return cmd_morning(args)
    if intent == "catch-up":
        return cmd_catch_up(args)
    if intent == "publish":
        return cmd_publish(args)
    if intent == "deep":
        return cmd_deep(args)
    if intent == "linkedin":
        return cmd_linkedin(args)
    if intent == "traces":
        return cmd_traces(args)
    if intent == "handoff":
        return cmd_handoff(args)
    if intent == "graph":
        return cmd_graph(args)
    if intent == "approve":
        return cmd_approve(args)
    if intent == "commands":
        return cmd_commands(args)
    if intent == "newsletter":
        return cmd_newsletter(args)
    if intent == "ask" or rest:
        args.query = rest or args.text
        return cmd_route(args)
    print(
        "의도 미감지 — morning/catch-up/publish/approve/graph/commands/linkedin/traces/handoff/ask",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--date", default="", help="YYYY-MM-DD")
    common.add_argument("--session", default="cli", help="session id")
    common.add_argument("--json", action="store_true")

    parser = argparse.ArgumentParser(description="Hermes Agent Phase 1")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_route = sub.add_parser("route", help="Memory Router 질의", parents=[common])
    p_route.add_argument("query")
    p_route.set_defaults(func=cmd_route)

    p_ask = sub.add_parser("ask", help="Memory Router 질의 (alias)", parents=[common])
    p_ask.add_argument("query")
    p_ask.set_defaults(func=cmd_route)

    p_m = sub.add_parser("morning", help="Morning intent pack", parents=[common])
    p_m.set_defaults(func=cmd_morning)

    p_cu = sub.add_parser("catch-up", help="Recent briefs summary", parents=[common])
    p_cu.add_argument("--days", type=int, default=3)
    p_cu.set_defaults(func=cmd_catch_up)

    p_pub = sub.add_parser("publish", help="Single channel publish (HITL gate)", parents=[common])
    p_pub.add_argument("channel", nargs="?", default="linkedin")
    p_pub.add_argument("--dry-run", action="store_true")
    p_pub.add_argument("--approve", action="store_true", help="HITL 우회 · 즉시 발행")
    p_pub.set_defaults(func=cmd_publish, approve=False)

    p_deep = sub.add_parser("deep", help="Deep research pack", parents=[common])
    p_deep.add_argument("topic", nargs="?", default="")
    p_deep.add_argument("--query", default="")
    p_deep.set_defaults(func=cmd_deep)

    p_pr = sub.add_parser("proactive", help="Proactive triggers", parents=[common])
    p_pr.set_defaults(func=cmd_proactive)

    p_br = sub.add_parser("bridge-sync", help="Personal → inbox candidates", parents=[common])
    p_br.set_defaults(func=cmd_bridge_sync)

    p_sess = sub.add_parser("session", help="Show/clear session", parents=[common])
    p_sess.add_argument("--clear", action="store_true")
    p_sess.set_defaults(func=cmd_session)

    p_auto = sub.add_parser("auto", help="Detect intent from text", parents=[common])
    p_auto.add_argument("text")
    p_auto.set_defaults(func=cmd_auto)

    p_li = sub.add_parser("linkedin", help="LinkedIn M3 sub-pipeline", parents=[common])
    p_li.add_argument("--validate", action="store_true")
    p_li.add_argument("--dry-run", action="store_true")
    p_li.set_defaults(func=cmd_linkedin)

    p_tr = sub.add_parser("traces", help="M4 performance report", parents=[common])
    p_tr.add_argument("--days", type=int, default=7)
    p_tr.set_defaults(func=cmd_traces)

    p_ho = sub.add_parser("handoff", help="Write session-handoff.md", parents=[common])
    p_ho.add_argument("--days", type=int, default=7)
    p_ho.set_defaults(func=cmd_handoff)

    p_gr = sub.add_parser("graph", help="Brief Graph Lite", parents=[common])
    p_gr.add_argument("--days", type=int, default=14)
    p_gr.add_argument("--write-unified", action="store_true")
    p_gr.set_defaults(func=cmd_graph, write_unified=False)

    p_ap = sub.add_parser("approve", help="HITL publish approve", parents=[common])
    p_ap.add_argument("channels", nargs="*", default=["all"])
    p_ap.set_defaults(func=cmd_approve)

    p_pend = sub.add_parser("pending", help="HITL publish queue status", parents=[common])
    p_pend.set_defaults(func=cmd_pending)

    p_cmd = sub.add_parser("commands", help="Command registry", parents=[common])
    p_cmd.set_defaults(func=cmd_commands)

    p_run = sub.add_parser("run", help="Run registry script command", parents=[common])
    p_run.add_argument("command_id")
    p_run.add_argument("extra", nargs="*")
    p_run.set_defaults(func=cmd_run)

    p_nl = sub.add_parser("newsletter", help="B2B newsletter (open/CTOR optimized)", parents=[common])
    p_nl.add_argument("--validate", action="store_true")
    p_nl.set_defaults(func=cmd_newsletter, validate=False)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
