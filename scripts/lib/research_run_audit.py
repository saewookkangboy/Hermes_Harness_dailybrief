"""Audit trail for keyword / research runs."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKDIR = Path.home() / "hermes-content-studio"
RUNS_DIR = WORKDIR / "content" / "research" / "_runs"


def fingerprint(keywords: str, mode: str, stamp: str) -> str:
    raw = f"{stamp}|{mode}|{(keywords or '').strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def write_run(
    *,
    stamp: str,
    mode: str,
    keywords: str,
    paths: dict[str, str],
    requester: str = "commander",
    extra: dict[str, Any] | None = None,
) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    fp = fingerprint(keywords, mode, stamp)
    run_id = f"{stamp}_{fp}"
    payload = {
        "run_id": run_id,
        "date": stamp,
        "mode": mode,
        "keywords": keywords,
        "fingerprint": fp,
        "requester": requester,
        "paths": paths,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }
    out = RUNS_DIR / f"{run_id}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def find_same_fingerprint(stamp: str, keywords: str, mode: str) -> Path | None:
    fp = fingerprint(keywords, mode, stamp)
    path = RUNS_DIR / f"{stamp}_{fp}.json"
    return path if path.exists() else None
