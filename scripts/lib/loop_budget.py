"""Content Loop LLM budget — cap · kill switch (결정적 체크)."""
from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from lib.content_quality_config import budget_config

WORKDIR = Path.home() / "hermes-content-studio"


def _ledger_path() -> Path:
    return Path(
        os.environ.get("HERMES_COST_LEDGER", str(WORKDIR / ".harness" / "cost-ledger.jsonl"))
    )


@dataclass
class BudgetStatus:
    ok: bool
    tokens_today: int = 0
    usd_today: float = 0.0
    token_cap: int = 0
    usd_cap: float = 0.0
    kill_active: bool = False
    detail: str = ""
    path: str = ""
    path_tokens: int = 0
    path_token_cap: int = 0


def _today_prefix() -> str:
    from lib.common import studio_today

    return studio_today()


def _iter_today_rows():
    ledger = _ledger_path()
    if not ledger.exists():
        return
    day = _today_prefix()
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not str(row.get("ts", "")).startswith(day):
            continue
        yield row


def read_today_spend() -> tuple[int, float]:
    tokens = 0
    usd = 0.0
    for row in _iter_today_rows():
        tokens += int(row.get("tokens") or 0)
        usd += float(row.get("usd") or 0.0)
    return tokens, usd


def read_today_spend_by_path() -> dict[str, tuple[int, float]]:
    by_path: dict[str, list[int | float]] = defaultdict(lambda: [0, 0.0])
    for row in _iter_today_rows():
        path = str(row.get("path") or "unknown")
        by_path[path][0] += int(row.get("tokens") or 0)
        by_path[path][1] += float(row.get("usd") or 0.0)
    return {k: (int(v[0]), float(v[1])) for k, v in by_path.items()}


def warn_threshold_pct() -> int:
    cfg = budget_config()
    return int(cfg.get("warn_threshold_pct") or 80)


def is_near_cap(tokens: int, token_cap: int) -> bool:
    if not token_cap:
        return False
    pct = warn_threshold_pct()
    return tokens * 100 >= token_cap * pct


def check_loop_budget() -> BudgetStatus:
    cfg = budget_config()
    kill_env = str(cfg.get("kill_switch_env") or "HERMES_LOOP_BUDGET_KILL")
    if os.environ.get(kill_env, "0") == "1":
        return BudgetStatus(ok=False, kill_active=True, detail=f"{kill_env}=1")

    token_cap = int(cfg.get("daily_token_cap") or 0)
    usd_cap = float(cfg.get("daily_usd_cap") or 0.0)
    tokens, usd = read_today_spend()

    if token_cap and tokens > token_cap:
        return BudgetStatus(
            ok=False,
            tokens_today=tokens,
            usd_today=usd,
            token_cap=token_cap,
            usd_cap=usd_cap,
            detail=f"token cap exceeded {tokens}>{token_cap}",
        )
    if usd_cap and usd > usd_cap:
        return BudgetStatus(
            ok=False,
            tokens_today=tokens,
            usd_today=usd,
            token_cap=token_cap,
            usd_cap=usd_cap,
            detail=f"usd cap exceeded {usd:.2f}>{usd_cap}",
        )

    path_caps = cfg.get("path_daily_token_caps") or {}
    if path_caps:
        by_path = read_today_spend_by_path()
        for path, cap_raw in path_caps.items():
            path_cap = int(cap_raw or 0)
            if not path_cap:
                continue
            path_tokens, _ = by_path.get(str(path), (0, 0.0))
            if path_tokens > path_cap:
                return BudgetStatus(
                    ok=False,
                    tokens_today=tokens,
                    usd_today=usd,
                    token_cap=token_cap,
                    usd_cap=usd_cap,
                    path=str(path),
                    path_tokens=path_tokens,
                    path_token_cap=path_cap,
                    detail=f"path {path} token cap exceeded {path_tokens}>{path_cap}",
                )

    return BudgetStatus(
        ok=True,
        tokens_today=tokens,
        usd_today=usd,
        token_cap=token_cap,
        usd_cap=usd_cap,
        detail="OK",
    )
