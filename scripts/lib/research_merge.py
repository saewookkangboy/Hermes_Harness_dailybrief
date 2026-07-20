"""Merge / replace helpers for keyword research into Brief SoT inputs."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from lib.brief_quality import canonicalize_url, title_token_overlap

WORKDIR = Path.home() / "hermes-content-studio"
RESEARCH_DIR = WORKDIR / "content" / "research"


def load_yaml_keyword_config() -> dict:
    cfg_path = WORKDIR / "config" / "research-brief.yaml"
    try:
        import yaml  # type: ignore

        if cfg_path.exists():
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            return dict(cfg.get("keyword_research") or {})
    except Exception:  # noqa: BLE001
        pass
    return {}


def require_approve_on_replace() -> bool:
    env = os.environ.get("HERMES_REQUIRE_APPROVE_ON_REPLACE", "").strip()
    if env in ("0", "false", "False"):
        return False
    if env in ("1", "true", "True"):
        return True
    return bool(load_yaml_keyword_config().get("require_approve_on_replace", True))


def overlap_threshold() -> float:
    try:
        return float(load_yaml_keyword_config().get("title_overlap_threshold", 0.55))
    except (TypeError, ValueError):
        return 0.55


def backup_brief(stamp: str) -> Path | None:
    src = RESEARCH_DIR / f"{stamp}_brief.md"
    if not src.exists():
        return None
    dst = RESEARCH_DIR / f"{stamp}_brief.prev.md"
    shutil.copy2(src, dst)
    return dst


def restore_brief(stamp: str) -> bool:
    prev = RESEARCH_DIR / f"{stamp}_brief.prev.md"
    live = RESEARCH_DIR / f"{stamp}_brief.md"
    if not prev.exists():
        return False
    shutil.copy2(prev, live)
    return True


def merge_result_lists(
    base: list[dict],
    keyword: list[dict],
    *,
    keyword_wins: bool = True,
) -> list[dict]:
    """Merge search hits; keyword rows win on URL / near-title collision."""
    thr = overlap_threshold()
    out: list[dict] = []
    seen: set[str] = set()

    def add(row: dict, *, prefer: bool) -> None:
        url = canonicalize_url(row.get("url") or "") or (row.get("url") or "")
        if not url:
            return
        title = row.get("title") or ""
        for i, existing in enumerate(out):
            eu = canonicalize_url(existing.get("url") or "") or (existing.get("url") or "")
            if eu == url or title_token_overlap(title, existing.get("title") or "") >= thr:
                if prefer and keyword_wins:
                    out[i] = {**row, "_from_keyword": True}
                return
        if url in seen:
            return
        seen.add(url)
        out.append({**row, "_from_keyword": prefer})

    for row in keyword:
        add(row, prefer=True)
    for row in base:
        add(row, prefer=False)
    return out


def merge_contexts(base_ctx: dict, keyword_ctx: dict) -> dict:
    merged = dict(base_ctx)
    merged["results"] = merge_result_lists(
        list(base_ctx.get("results") or []),
        list(keyword_ctx.get("results") or []),
    )
    merged["count"] = len(merged["results"])
    merged["keywords"] = keyword_ctx.get("keywords") or base_ctx.get("keywords")
    merged["mode"] = "merge"
    return merged


def write_context(stamp: str, ctx: dict, suffix: str = "") -> Path:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    name = f"_search_context_{stamp}{suffix}.json"
    path = RESEARCH_DIR / name
    path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_context(stamp: str, suffix: str = "") -> dict[str, Any]:
    path = RESEARCH_DIR / f"_search_context_{stamp}{suffix}.json"
    return json.loads(path.read_text(encoding="utf-8"))
