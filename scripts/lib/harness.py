"""Harness engineering utilities — timing, traces, cost ledger.

Reference: https://github.com/walkinglabs/awesome-harness-engineering
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import yaml

WORKDIR = Path.home() / "hermes-content-studio"
HARNESS_DIR = WORKDIR / ".harness"
CONFIG_PATH = WORKDIR / "config" / "harness.yaml"


def load_harness_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_sla(stage: str) -> int | None:
    cfg = load_harness_config()
    return (cfg.get("performance") or {}).get("sla_seconds", {}).get(stage)


def get_baseline(stage: str) -> int | None:
    cfg = load_harness_config()
    return (cfg.get("eval") or {}).get("baseline_seconds", {}).get(stage)


def get_search_workers() -> int:
    cfg = load_harness_config()
    return int((cfg.get("performance") or {}).get("parallel_search_workers", 4))


@contextmanager
def timed_stage(name: str) -> Generator[dict[str, Any], None, None]:
    """Context manager that records stage duration and SLA warnings."""
    record: dict[str, Any] = {"stage": name, "started_at": _iso_now()}
    start = time.perf_counter()
    try:
        yield record
    finally:
        elapsed = time.perf_counter() - start
        record["elapsed_seconds"] = round(elapsed, 2)
        record["finished_at"] = _iso_now()
        sla = get_sla(name)
        if sla and elapsed > sla:
            record["sla_breach"] = True
            print(f"⚠️  SLA 초과 [{name}]: {elapsed:.1f}s > {sla}s", flush=True)
        append_trace(record)


def append_trace(record: dict[str, Any]) -> None:
    HARNESS_DIR.mkdir(parents=True, exist_ok=True)
    traces_dir = HARNESS_DIR / "traces"
    traces_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = traces_dir / f"trace-{stamp}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_cost(entry: dict[str, Any]) -> None:
    HARNESS_DIR.mkdir(parents=True, exist_ok=True)
    path = HARNESS_DIR / "cost-ledger.jsonl"
    entry.setdefault("timestamp", _iso_now())
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def save_eval_results(results: dict[str, Any]) -> Path:
    HARNESS_DIR.mkdir(parents=True, exist_ok=True)
    path = HARNESS_DIR / "eval-results.json"
    results["recorded_at"] = _iso_now()
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def check_regression(stage: str, elapsed: float) -> dict[str, Any]:
    baseline = get_baseline(stage)
    cfg = load_harness_config()
    threshold_pct = float((cfg.get("eval") or {}).get("regression_threshold_pct", 25))
    if not baseline:
        return {"stage": stage, "regression": False}
    pct = ((elapsed - baseline) / baseline) * 100
    return {
        "stage": stage,
        "elapsed": round(elapsed, 2),
        "baseline": baseline,
        "delta_pct": round(pct, 1),
        "regression": pct > threshold_pct,
    }


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
