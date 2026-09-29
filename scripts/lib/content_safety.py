"""Shared content-safety blocklist for every stage that ingests web sources.

Single source of truth: `config/newsletter.yaml` → `safety` (the M2b newsletter
gate already reads it). M1 research intake, the brief graph (`build-graph.py`)
and the wiki seed use the same lists so an unsafe URL is stopped before it
reaches the brief, graph.db or content/wiki — not only at the newsletter.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SAFETY_CONFIG = REPO_ROOT / "config" / "newsletter.yaml"

DEFAULT_URL_SUBSTRINGS = ("undress", "undresser", "nsfw", "deepnude", "nudify")
DEFAULT_TITLE_SUBSTRINGS = ("Undress", "NSFW", "Nudify")
# Search-engine ad redirects are never citable sources.
AD_CLICK_SUBSTRINGS = ("bing.com/aclick", "googleadservices.com", "doubleclick.net")


@lru_cache(maxsize=1)
def _lists() -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        import yaml  # type: ignore

        cfg = yaml.safe_load(SAFETY_CONFIG.read_text(encoding="utf-8")) or {}
        safety = cfg.get("safety") or {}
        urls = tuple(str(s) for s in safety.get("block_url_substrings") or DEFAULT_URL_SUBSTRINGS)
        titles = tuple(str(s) for s in safety.get("block_title_substrings") or DEFAULT_TITLE_SUBSTRINGS)
        return urls, titles
    except Exception:  # noqa: BLE001 — missing yaml/config must not disable the check
        return DEFAULT_URL_SUBSTRINGS, DEFAULT_TITLE_SUBSTRINGS


def is_ad_click(url: str) -> bool:
    u = (url or "").lower()
    return any(s in u for s in AD_CLICK_SUBSTRINGS)


def is_unsafe(url: str = "", title: str = "", *extra: str) -> bool:
    """True when a source matches the shared NSFW blocklist or is an ad-click URL."""
    if is_ad_click(url):
        return True
    url_needles, title_needles = _lists()
    blob = " ".join([url or "", title or "", *extra]).lower()
    return any(n.lower() in blob for n in (*url_needles, *title_needles))
