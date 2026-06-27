"""Competitive Watch Agent — Brief Graph · 키워드 감시 (결정적)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from lib.brief_graph import build_brief_graph, load_brief_graph, save_brief_graph
from lib.common import studio_today, truncate

WORKDIR = Path.home() / "hermes-content-studio"
CONFIG_PATH = WORKDIR / "config" / "competitive-watch.yaml"
STATE_PATH = WORKDIR / ".harness" / "competitive-watch-state.json"
LOGS_DIR = WORKDIR / "content" / "logs"


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"version": 1, "last_run": "", "streaks": {}, "topic_keys": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "last_run": "", "streaks": {}, "topic_keys": []}


def _save_state(data: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _match_entity(topic_key: str, title: str, entities: list[dict]) -> str | None:
    blob = f"{topic_key} {title}".lower()
    for ent in entities:
        for kw in ent.get("keywords") or []:
            if kw.lower() in blob:
                return ent.get("id", ent.get("label", ""))
    return None


def run_competitive_watch(*, window_days: int | None = None, write_report: bool = True) -> dict[str, Any]:
    cfg = _load_config()
    days = window_days or int(cfg.get("window_days", 14))
    entities = cfg.get("watch_entities") or []
    alerts_cfg = cfg.get("alerts") or {}
    min_streak = int(alerts_cfg.get("new_topic_streak_min", 2))
    streak_delta = int(alerts_cfg.get("rising_streak_delta", 1))

    graph = build_brief_graph(days)
    save_brief_graph(days)
    prev = _load_state()
    prev_streaks: dict[str, int] = prev.get("streaks") or {}
    prev_keys: set[str] = set(prev.get("topic_keys") or [])

    current_keys = {s.get("topic_key", "") for s in graph.get("streaks", [])}
    new_keys = sorted(current_keys - prev_keys)

    rising: list[dict] = []
    by_entity: dict[str, list[dict]] = {}
    for streak in graph.get("streaks", []):
        key = streak.get("topic_key", "")
        days_s = int(streak.get("streak_days", 0))
        title = streak.get("latest_title", key)
        prev_d = int(prev_streaks.get(key, 0))
        if days_s >= min_streak and days_s > prev_d + streak_delta - 1:
            rising.append(streak)
        ent = _match_entity(key, title, entities)
        if ent:
            by_entity.setdefault(ent, []).append(streak)

    stamp = studio_today()
    report = {
        "stamp": stamp,
        "window_days": days,
        "new_topic_keys": new_keys,
        "rising_streaks": rising[:10],
        "by_entity": {k: len(v) for k, v in by_entity.items()},
        "node_count": graph.get("node_count", 0),
    }

    if write_report:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        path = LOGS_DIR / f"{stamp}_competitive-watch.md"
        path.write_text(format_watch_digest(report, graph, by_entity), encoding="utf-8")
        report["report_path"] = str(path)

    _save_state(
        {
            "version": 1,
            "streaks": {s.get("topic_key"): s.get("streak_days", 0) for s in graph.get("streaks", [])},
            "topic_keys": sorted(current_keys),
        }
    )
    return report


def format_watch_digest(
    report: dict[str, Any],
    graph: dict,
    by_entity: dict[str, list[dict]],
) -> str:
    lines = [
        f"# Competitive Watch — {report.get('stamp')}",
        "",
        f"- window: {report.get('window_days')}d · nodes: {report.get('node_count')}",
        "",
        "## 신규 topic_key",
    ]
    new_keys = report.get("new_topic_keys") or []
    if new_keys:
        lines.extend([f"- `{k}`" for k in new_keys[:12]])
    else:
        lines.append("- (없음)")

    lines.extend(["", "## 상승 streak"])
    rising = report.get("rising_streaks") or []
    if rising:
        for s in rising[:8]:
            lines.append(
                f"- **{s.get('topic_key')}** ({s.get('streak_days')}d) — "
                f"{truncate(s.get('latest_title', ''), 50)}"
            )
    else:
        lines.append("- (없음)")

    lines.extend(["", "## 엔티티별 관측"])
    cfg_entities = (_load_config().get("watch_entities") or [])
    label_map = {e.get("id"): e.get("label") for e in cfg_entities}
    counts = report.get("by_entity") or {}
    for eid, count in sorted(counts.items(), key=lambda x: -x[1]):
        label = label_map.get(eid, eid)
        lines.append(f"- **{label}:** {count} topic(s)")
        for s in (by_entity.get(eid) or [])[:2]:
            lines.append(f"  - {s.get('topic_key')}: {truncate(s.get('latest_title', ''), 45)}")

    lines.extend(["", "## Graph top streaks"])
    for s in (graph.get("streaks") or [])[:5]:
        lines.append(
            f"- {s.get('topic_key')} — {s.get('streak_days')}d · "
            f"{truncate(s.get('latest_title', ''), 45)}"
        )
    return "\n".join(lines)


def format_watch_summary(report: dict[str, Any]) -> str:
    new_n = len(report.get("new_topic_keys") or [])
    rise_n = len(report.get("rising_streaks") or [])
    lines = [
        f"👁 Competitive Watch · {report.get('stamp')}",
        "",
        f"신규 topic: {new_n} · 상승 streak: {rise_n}",
    ]
    if report.get("report_path"):
        rel = str(report["report_path"]).replace(str(WORKDIR) + "/", "")
        lines.append(f"📋 `{rel}`")
    return "\n".join(lines)
