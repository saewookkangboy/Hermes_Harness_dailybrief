"""Research staging store — separate from publish HITL (.harness/publish-queue)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKDIR = Path.home() / "hermes-content-studio"
STAGING_ROOT = WORKDIR / "content" / "research" / "_staging"
RESEARCH_DIR = WORKDIR / "content" / "research"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_pending() -> list[dict[str, Any]]:
    if not STAGING_ROOT.exists():
        return []
    items: list[dict[str, Any]] = []
    for meta in sorted(STAGING_ROOT.glob("*/meta.json"), reverse=True):
        try:
            items.append(json.loads(meta.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return items


def format_pending_status() -> str:
    items = list_pending()
    if not items:
        return "research staging: (empty)"
    lines = ["research staging pending:"]
    for it in items:
        lines.append(
            f"- {it.get('run_id')} · {it.get('mode')} · kw={it.get('keywords')!r} · "
            f"insights={it.get('insight_count', '?')} · {it.get('created_at', '')}"
        )
    return "\n".join(lines)


def write_staging(
    *,
    run_id: str,
    stamp: str,
    mode: str,
    keywords: str,
    brief_text: str,
    evidence: dict | None = None,
    insight_count: int = 0,
) -> Path:
    dest = STAGING_ROOT / run_id
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "brief.md").write_text(brief_text, encoding="utf-8")
    if evidence is not None:
        (dest / "evidence.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    meta = {
        "run_id": run_id,
        "date": stamp,
        "mode": mode,
        "keywords": keywords,
        "insight_count": insight_count,
        "created_at": _now(),
        "brief_path": str(dest / "brief.md"),
    }
    (dest / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest


def approve(run_id: str | None = None, *, all_pending: bool = False) -> list[Path]:
    """Commit staging brief(s) to live SoT. Returns committed brief paths."""
    from lib.research_merge import backup_brief

    items = list_pending()
    if not items:
        return []
    if all_pending:
        selected = items
    elif run_id:
        selected = [i for i in items if i.get("run_id") == run_id]
    else:
        selected = items[:1]
    committed: list[Path] = []
    for it in selected:
        rid = it["run_id"]
        stamp = it["date"]
        src = STAGING_ROOT / rid / "brief.md"
        if not src.exists():
            continue
        backup_brief(stamp)
        live = RESEARCH_DIR / f"{stamp}_brief.md"
        # transactional: write temp then replace
        tmp = RESEARCH_DIR / f".{stamp}_brief.md.tmp"
        shutil.copy2(src, tmp)
        tmp.replace(live)
        ev = STAGING_ROOT / rid / "evidence.json"
        if ev.exists():
            shutil.copy2(ev, RESEARCH_DIR / f"_evidence_{stamp}.json")
        shutil.rmtree(STAGING_ROOT / rid, ignore_errors=True)
        committed.append(live)
    return committed
