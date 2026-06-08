"""Brief Graph Lite — 날짜 간 topic_key 엣지 · 차이 열."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.brief_gate import brief_path
from lib.common import studio_today, truncate
from lib.content_quality import Insight, _insight_topic_key, parse_brief

WORKDIR = Path.home() / "hermes-content-studio"
RESEARCH = WORKDIR / "content" / "research"
GRAPH_PATH = RESEARCH / "_brief_graph.json"


def _list_brief_stamps(days: int = 14) -> list[str]:
    if not RESEARCH.is_dir():
        return []
    stamps: list[str] = []
    for path in RESEARCH.glob("*_brief.md"):
        stamp = path.name.replace("_brief.md", "")
        if re.match(r"^\d{4}-\d{2}-\d{2}$", stamp):
            stamps.append(stamp)
    stamps.sort(reverse=True)
    return stamps[:days]


def _insight_node(stamp: str, idx: int, ins: Insight) -> dict:
    key = _insight_topic_key(ins)
    return {
        "stamp": stamp,
        "index": idx,
        "topic_key": key,
        "title": ins.korean_title,
        "url": ins.url,
    }


def build_brief_graph(days: int = 14) -> dict:
    """Scan briefs → nodes + topic streaks."""
    stamps = _list_brief_stamps(days)
    nodes: list[dict] = []
    by_key: dict[str, list[dict]] = {}

    for stamp in stamps:
        path = brief_path(stamp)
        if not path.exists():
            continue
        _, insights = parse_brief(path.read_text(encoding="utf-8"))
        for i, ins in enumerate(insights[:7], 1):
            node = _insight_node(stamp, i, ins)
            nodes.append(node)
            by_key.setdefault(node["topic_key"], []).append(node)

    edges: list[dict] = []
    streaks: list[dict] = []
    for key, group in by_key.items():
        group_sorted = sorted(group, key=lambda n: n["stamp"], reverse=True)
        stamps_seen = [g["stamp"] for g in group_sorted]
        streak = 1
        for i in range(1, len(stamps_seen)):
            d0 = datetime.strptime(stamps_seen[i - 1], "%Y-%m-%d").date()
            d1 = datetime.strptime(stamps_seen[i], "%Y-%m-%d").date()
            if (d0 - d1).days == 1:
                streak += 1
            else:
                break
        streaks.append(
            {
                "topic_key": key,
                "latest_title": group_sorted[0]["title"],
                "streak_days": streak,
                "appearances": len(group_sorted),
                "dates": stamps_seen[:5],
            }
        )
        for i in range(len(group_sorted) - 1):
            edges.append(
                {
                    "topic_key": key,
                    "from": group_sorted[i + 1]["stamp"],
                    "to": group_sorted[i]["stamp"],
                    "relation": "continues",
                }
            )

    graph = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": days,
        "node_count": len(nodes),
        "nodes": nodes,
        "edges": edges,
        "streaks": sorted(streaks, key=lambda s: (-s["streak_days"], -s["appearances"])),
    }
    return graph


def save_brief_graph(days: int = 14) -> Path:
    data = build_brief_graph(days)
    GRAPH_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return GRAPH_PATH


def load_brief_graph() -> dict:
    if not GRAPH_PATH.exists():
        return build_brief_graph()
    try:
        return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return build_brief_graph()


def diff_hint_for_insight(stamp: str, ins: Insight, graph: dict | None = None) -> str:
    """이전 브리프 대비 차이 한 줄."""
    graph = graph or load_brief_graph()
    key = _insight_topic_key(ins)
    streaks = {s["topic_key"]: s for s in graph.get("streaks", [])}
    s = streaks.get(key)
    if not s:
        return "신규 주제"
    if s["streak_days"] >= 3:
        return f"{s['streak_days']}일 연속 · AX 타임라인"
    if s["streak_days"] >= 2:
        return f"{s['streak_days']}일 연속"
    if stamp in (s.get("dates") or [])[:1]:
        return "재등장"
    return "이전 대비 갱신"


def build_brief_graph_table(stamp: str, insights: list[Insight], days: int = 14) -> str:
    """Unified Context용 — 발췌 표 + 이전 브리프와의 차이 열."""
    graph = build_brief_graph(days)
    count = min(len(insights), 7)
    lines = [
        "## Research Brief 발췌 (Graph)",
        "",
        f"**브리프 날짜:** `{stamp}` · **Top {count}** · graph window {days}일",
        "",
        "| # | 인사이트 | 핵심 요약 | 이전 브리프와의 차이 | 출처 |",
        "|---:|---|---|---|---|",
    ]

    def cell(text: str, n: int) -> str:
        return truncate(str(text or "—"), n).replace("|", "\\|").replace("\n", " ")

    for i, ins in enumerate(insights[:7], 1):
        diff = diff_hint_for_insight(stamp, ins, graph)
        lines.append(
            f"| {i} | {cell(ins.korean_title, 48)} | {cell(ins.korean_summary, 80)} "
            f"| {cell(diff, 40)} | {ins.url or '—'} |"
        )
    top_streaks = graph.get("streaks", [])[:3]
    if top_streaks:
        lines.extend(["", "### Topic Streaks (Top 3)"])
        for s in top_streaks:
            lines.append(
                f"- **{s['topic_key']}** · {s['streak_days']}일 연속 · "
                f"{truncate(s['latest_title'], 40)}"
            )
    return "\n".join(lines)


def patch_unified_context(stamp: str, days: int = 14) -> Path | None:
    """unified-context.md 의 Brief 발췌를 Graph 표로 교체."""
    from lib.brief_gate import brief_path

    pkg = WORKDIR / "content" / "packages" / f"{stamp}_unified-context.md"
    if not pkg.exists() or not brief_path(stamp).exists():
        return None
    _, insights = parse_brief(brief_path(stamp).read_text(encoding="utf-8"))
    graph_table = build_brief_graph_table(stamp, insights, days)
    text = pkg.read_text(encoding="utf-8")
    marker_start = "## Research Brief 발췌"
    marker_graph = "## Research Brief 발췌 (Graph)"
    if marker_graph in text:
        return pkg
    if marker_start not in text:
        text = text.rstrip() + "\n\n" + graph_table + "\n"
    else:
        head, _ = text.split(marker_start, 1)
        rest = text.split(marker_start, 1)[1]
        if "\n## " in rest:
            _, tail = rest.split("\n## ", 1)
            tail = "\n## " + tail
        else:
            tail = ""
        text = head.rstrip() + "\n\n" + graph_table + tail
    pkg.write_text(text, encoding="utf-8")
    save_brief_graph(days)
    return pkg


def format_graph_summary(days: int = 14) -> str:
    graph = build_brief_graph(days)
    lines = [
        f"🕸 Brief Graph · {days}일",
        "",
        f"노드: {graph['node_count']} · 엣지: {len(graph.get('edges', []))}",
        "",
        "| topic_key | 연속 | 등장 | 최신 제목 |",
        "|-----------|-----:|-----:|---|",
    ]
    for s in graph.get("streaks", [])[:7]:
        lines.append(
            f"| {s['topic_key']} | {s['streak_days']} | {s['appearances']} | "
            f"{truncate(s['latest_title'], 36)} |"
        )
    return "\n".join(lines)
