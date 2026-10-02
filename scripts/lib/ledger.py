"""cost-ledger / trace 원장 읽기·쓰기. stdlib only.

기존 loop_budget 형식(path/tokens/usd)과 F1 형식(stage/tokens_in/out)을
모두 읽는다. 신규 append는 F1 형식으로 기록한다.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

STUDIO = Path(os.environ.get("HERMES_STUDIO", os.environ.get("HERMES_WORKDIR", Path(__file__).resolve().parents[2])))
HARNESS = STUDIO / ".harness"
LEDGER = Path(os.environ.get("HERMES_COST_LEDGER", str(HARNESS / "cost-ledger.jsonl")))
TRACES = HARNESS / "traces"


@dataclass
class CostEntry:
    ts: str
    stage: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    run_id: str
    deterministic: bool = False
    note: str = ""

    @staticmethod
    def now(
        stage: str,
        *,
        model: str = "none",
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
        run_id: str = "",
        deterministic: bool = False,
        note: str = "",
    ) -> "CostEntry":
        return CostEntry(
            ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            stage=stage,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            run_id=run_id,
            deterministic=deterministic,
            note=note,
        )


def append(entry: CostEntry) -> None:
    """원장에 append. 실패해도 파이프라인을 죽이지 않는다 (best-effort)."""
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    except OSError:
        pass


def _parse_since(since: str) -> datetime:
    """'7d' | '24h' | '2026-07-01' 을 datetime으로."""
    now = datetime.now(timezone.utc)
    if since.endswith("d"):
        return now - timedelta(days=int(since[:-1]))
    if since.endswith("h"):
        return now - timedelta(hours=int(since[:-1]))
    return datetime.fromisoformat(since).replace(tzinfo=timezone.utc)


def _parse_ts(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except ValueError:
        return None


def _normalize(rec: dict) -> dict | None:
    """레거시(path/tokens/usd) → 정규 스키마. GATE-TEST 는 무시."""
    run_id = str(rec.get("run_id") or "")
    if run_id.startswith("GATE-TEST"):
        return None
    note = str(rec.get("note") or "")
    if "GATE-TEST" in note or note.startswith("void"):
        return None

    stage = rec.get("stage") or rec.get("path") or "unknown"
    if "tokens_in" in rec or "tokens_out" in rec:
        tokens_in = int(rec.get("tokens_in") or 0)
        tokens_out = int(rec.get("tokens_out") or 0)
    else:
        tokens_in = int(rec.get("tokens") or 0)
        tokens_out = 0
    cost = float(rec.get("cost_usd") if "cost_usd" in rec else (rec.get("usd") or 0.0))
    ts = rec.get("ts") or rec.get("timestamp") or ""
    return {
        "ts": ts,
        "stage": stage,
        "model": rec.get("model") or "none",
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost,
        "run_id": run_id,
        "deterministic": bool(rec.get("deterministic", False)),
        "note": note,
    }


def read(since: str = "7d", stage: str | None = None) -> list[dict]:
    if not LEDGER.exists():
        return []
    cutoff = _parse_since(since)
    out: list[dict] = []
    with LEDGER.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            rec = _normalize(raw)
            if not rec:
                continue
            ts = _parse_ts(rec["ts"])
            if ts is None or ts < cutoff:
                continue
            if stage and rec.get("stage") != stage:
                continue
            out.append(rec)
    return out


def aggregate(since: str = "7d") -> dict[str, dict]:
    """단계별 집계. {stage: {runs, tokens_in, tokens_out, cost_usd, ...}}"""
    agg: dict[str, dict] = {}
    for rec in read(since):
        s = agg.setdefault(
            rec["stage"],
            {
                "runs": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "max_in": 0,
                "deterministic": rec.get("deterministic", False),
            },
        )
        s["runs"] += 1
        s["tokens_in"] += rec.get("tokens_in", 0)
        s["tokens_out"] += rec.get("tokens_out", 0)
        s["cost_usd"] += rec.get("cost_usd", 0.0)
        s["max_in"] = max(s["max_in"], rec.get("tokens_in", 0))
        if rec.get("deterministic"):
            s["deterministic"] = True
    for s in agg.values():
        s["avg_in"] = round(s["tokens_in"] / s["runs"]) if s["runs"] else 0
        s["avg_out"] = round(s["tokens_out"] / s["runs"]) if s["runs"] else 0
    return agg
