"""M4 Performance Analytics — traces · Notion tier · SLA 리포트."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from lib.harness import get_baseline, get_sla, load_harness_config

WORKDIR = Path.home() / "hermes-content-studio"
TRACES_DIR = WORKDIR / ".harness" / "traces"
STATE_PATH = WORKDIR / "content" / ".notion-archive-state.json"
M4_SNAPSHOT = WORKDIR / ".harness" / "m4-snapshot.json"


def _parse_ts(raw: str) -> datetime | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def load_trace_records(days: int = 7) -> list[dict[str, Any]]:
    """Load trace jsonl entries from the last N days."""
    if not TRACES_DIR.is_dir():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records: list[dict[str, Any]] = []
    for path in sorted(TRACES_DIR.glob("trace-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            ts = _parse_ts(rec.get("finished_at") or rec.get("started_at") or "")
            if ts and ts < cutoff:
                continue
            records.append(rec)
    return records


def aggregate_stages(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-stage stats: count, avg, min, max, sla_breaches."""
    buckets: dict[str, list[float]] = defaultdict(list)
    breaches: dict[str, int] = defaultdict(int)
    for rec in records:
        stage = str(rec.get("stage") or "unknown")
        elapsed = rec.get("elapsed_seconds") or rec.get("elapsed")
        if elapsed is None:
            continue
        try:
            val = float(elapsed)
        except (TypeError, ValueError):
            continue
        buckets[stage].append(val)
        if rec.get("sla_breach"):
            breaches[stage] += 1
    out: dict[str, dict[str, Any]] = {}
    for stage, vals in buckets.items():
        sla = get_sla(stage)
        baseline = get_baseline(stage)
        avg = sum(vals) / len(vals)
        out[stage] = {
            "count": len(vals),
            "avg_seconds": round(avg, 2),
            "min_seconds": round(min(vals), 2),
            "max_seconds": round(max(vals), 2),
            "sla_seconds": sla,
            "sla_breaches": breaches.get(stage, 0),
            "baseline_seconds": baseline,
            "vs_baseline_pct": round(((avg - baseline) / baseline) * 100, 1) if baseline else None,
        }
    return out


def notion_tier_stats() -> dict[str, Any]:
    """Draft vs canonical ratio from archive state."""
    if not STATE_PATH.exists():
        return {"pages": 0, "draft_count": 0, "canonical_count": 0, "draft_ratio_pct": 0}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"pages": 0, "draft_count": 0, "canonical_count": 0, "draft_ratio_pct": 0}
    pages = state.get("pages") or {}
    draft = canonical = 0
    for meta in pages.values():
        if not isinstance(meta, dict):
            continue
        tier = str(meta.get("tier") or meta.get("quality_tier") or "canonical").lower()
        if "draft" in tier:
            draft += 1
        else:
            canonical += 1
    total = draft + canonical
    return {
        "pages": total,
        "draft_count": draft,
        "canonical_count": canonical,
        "draft_ratio_pct": round((draft / total) * 100, 1) if total else 0,
    }


def newsletter_kpis(stamp: str) -> dict[str, Any]:
    """M4 — 뉴스레터 A/B 제목·Notion 동기화 KPI."""
    scores_path = WORKDIR / "content" / "newsletter" / f"{stamp}_newsletter_subject-scores.json"
    out: dict[str, Any] = {"stamp": stamp, "scores_available": False}
    if scores_path.exists():
        try:
            data = json.loads(scores_path.read_text(encoding="utf-8"))
            winner = data.get("winner") or {}
            out.update(
                {
                    "scores_available": True,
                    "winner_score": winner.get("score"),
                    "winner_title": winner.get("text"),
                    "winner_chars": winner.get("chars"),
                    "candidate_count": len(data.get("candidates") or []),
                }
            )
        except (json.JSONDecodeError, OSError):
            pass
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            pages = state.get("pages") or {}
            for cat in ("newsletter", "newsletter_html"):
                meta = pages.get(f"{stamp}/{cat}") or pages.get(f"{stamp}/{cat}@draft")
                if isinstance(meta, dict):
                    out[f"notion_{cat}"] = {
                        "tier": meta.get("tier"),
                        "score": meta.get("quality_score"),
                        "url": meta.get("url"),
                    }
        except (json.JSONDecodeError, OSError):
            pass
    try:
        from lib.newsletter_ctor import ctor_summary_for_m4

        out["ctor"] = ctor_summary_for_m4()
    except ImportError:
        pass
    return out


def build_m4_report(days: int = 7, *, stamp: str = "") -> dict[str, Any]:
    records = load_trace_records(days)
    stages = aggregate_stages(records)
    notion = notion_tier_stats()
    cfg = load_harness_config()
    analytics_mode = "simulation"
    channel_metrics: dict[str, Any] = {}
    try:
        from lib.m4_channel_metrics import load_channel_metrics, m4_analytics_mode, sync_ctor_to_channel_metrics

        sync_ctor_to_channel_metrics()
        analytics_mode = m4_analytics_mode()
        channel_metrics = load_channel_metrics()
    except ImportError:
        pass
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": days,
        "trace_count": len(records),
        "stages": stages,
        "notion_tiers": notion,
        "harness_version": (cfg.get("harness") or {}).get("version", ""),
        "analytics_mode": analytics_mode,
        "channel_metrics": channel_metrics,
    }
    if stamp:
        report["newsletter"] = newsletter_kpis(stamp)
    return report


def format_m4_report(days: int = 7) -> str:
    data = build_m4_report(days)
    lines = [
        f"📊 M4 Performance · 최근 {days}일",
        "",
        f"트레이스: {data['trace_count']}건",
        "",
        "| Stage | n | avg | SLA | breach |",
        "|-------|---|-----|-----|--------|",
    ]
    for stage, s in sorted(data["stages"].items()):
        sla = s.get("sla_seconds") or "—"
        lines.append(
            f"| {stage} | {s['count']} | {s['avg_seconds']}s | {sla}s | {s['sla_breaches']} |"
        )
    nt = data["notion_tiers"]
    lines.extend(
        [
            "",
            f"Notion tier: canonical {nt['canonical_count']} · draft {nt['draft_count']} "
            f"({nt['draft_ratio_pct']}%)",
        ]
    )
    regressions = [
        f"{st}: +{s['vs_baseline_pct']}%"
        for st, s in data["stages"].items()
        if s.get("vs_baseline_pct") and s["vs_baseline_pct"] > 25
    ]
    if regressions:
        lines.extend(["", "⚠️ 회귀:", *regressions])
    else:
        lines.extend(["", "✅ SLA 회귀 없음"])
    nl = data.get("newsletter")
    if nl and nl.get("scores_available"):
        lines.extend(
            [
                "",
                f"Newsletter {nl.get('stamp')}: winner score {nl.get('winner_score')} · "
                f"{nl.get('candidate_count')} candidates",
            ]
        )
    return "\n".join(lines)


def save_m4_snapshot(days: int = 7) -> Path:
    data = build_m4_report(days)
    M4_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    M4_SNAPSHOT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return M4_SNAPSHOT


def record_agent_trace(
    intent: str,
    action: str,
    elapsed_ms: float,
    *,
    stamp: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    """Agent intent 실행을 M4 trace에 기록."""
    from lib.harness import append_trace

    rec: dict[str, Any] = {
        "stage": f"agent_{intent}",
        "action": action,
        "elapsed_seconds": round(elapsed_ms / 1000, 3),
        "stamp": stamp,
        "source": "hermes-agent",
    }
    if extra:
        rec.update(extra)
    sla = get_sla("agent_intent")
    if sla and rec["elapsed_seconds"] > sla:
        rec["sla_breach"] = True
    append_trace(rec)
