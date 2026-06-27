"""M4 채널 실측 메트릭 — CTOR + 외부 import (결정적)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.newsletter_ctor import ctor_summary_for_m4, list_records

WORKDIR = Path.home() / "hermes-content-studio"
METRICS_PATH = WORKDIR / ".harness" / "channel-metrics.json"


def load_channel_metrics() -> dict[str, Any]:
    if not METRICS_PATH.exists():
        return {"version": 1, "sources": [], "channels": {}}
    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "sources": [], "channels": {}}


def save_channel_metrics(data: dict[str, Any]) -> Path:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        METRICS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return METRICS_PATH


def sync_ctor_to_channel_metrics() -> dict[str, Any]:
    """CTOR 기록 → channel-metrics newsletter 채널 동기화."""
    data = load_channel_metrics()
    records = list_records(limit=30)
    ctor = ctor_summary_for_m4()
    channels = data.setdefault("channels", {})
    channels["newsletter"] = {
        "mode": "live",
        "source": "newsletter-ctor-metrics",
        "campaign_count": ctor.get("count", 0),
        "avg_ctor_pct": ctor.get("avg_ctor_pct"),
        "healthy_count": ctor.get("healthy_count"),
        "latest": ctor.get("latest"),
        "records": records[:10],
    }
    sources = set(data.get("sources") or [])
    sources.add("ctor")
    data["sources"] = sorted(sources)
    save_channel_metrics(data)
    return data


def import_external_metrics(path: Path, channel: str) -> dict[str, Any]:
    """외부 JSON(LinkedIn/GA4 export) → channel-metrics 병합."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    data = load_channel_metrics()
    channels = data.setdefault("channels", {})
    channels[channel] = {
        "mode": "live",
        "source": str(path),
        "imported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": raw if isinstance(raw, dict) else {"rows": raw},
    }
    sources = set(data.get("sources") or [])
    sources.add(f"import:{channel}")
    data["sources"] = sorted(sources)
    save_channel_metrics(data)
    return data


def m4_analytics_mode() -> str:
    """simulation | live — channel-metrics 또는 CTOR 존재 시 live."""
    data = load_channel_metrics()
    channels = data.get("channels") or {}
    if any((c.get("mode") == "live" for c in channels.values() if isinstance(c, dict))):
        return "live"
    if list_records(limit=1):
        return "live"
    return "simulation"


def format_channel_metrics_block() -> str:
    sync_ctor_to_channel_metrics()
    data = load_channel_metrics()
    mode = m4_analytics_mode()
    lines = [f"**M4 모드:** {mode}", ""]
    for ch, meta in sorted((data.get("channels") or {}).items()):
        if not isinstance(meta, dict):
            continue
        if ch == "newsletter":
            lines.append(
                f"- **newsletter:** CTOR avg {meta.get('avg_ctor_pct', '—')}% · "
                f"campaigns {meta.get('campaign_count', 0)}"
            )
        else:
            lines.append(f"- **{ch}:** imported ({meta.get('source', '—')})")
    return "\n".join(lines) if len(lines) > 2 else f"**M4 모드:** {mode} · 실측 없음"
