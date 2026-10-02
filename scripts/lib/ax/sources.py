"""M1c 멀티소스 수집 — web/news(ddgs) · GitHub · arXiv · Hacker News. 소스별 실패 격리."""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from lib.ax.config import load_config
from lib.ax.lens_queries import LensQuery

try:
    from ddgs import DDGS  # type: ignore
except ImportError:  # requirements.txt — web/news 소스만 비활성
    DDGS = None

USER_AGENT = "hermes-content-studio/topic-pack (+https://github.com)"
_ATOM = "{http://www.w3.org/2005/Atom}"

Row = dict[str, Any]


def _row(lq: LensQuery, *, title: str, url: str, snippet: str = "", published: str = "", meta: dict | None = None) -> Row:
    return {
        "lens": lq.lens,
        "source_type": lq.source,
        "query": lq.query,
        "title": (title or "").strip(),
        "url": (url or "").strip(),
        "snippet": (snippet or "").strip()[:500],
        "published": published or "",
        "meta": meta or {},
    }


def _http_get(url: str, timeout: float, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed https hosts
        return resp.read()


def _ddgs():
    if DDGS is None:
        raise RuntimeError(f"ddgs not installed — {sys.executable} -m pip install ddgs")
    return DDGS


def _ddgs_search(kind: str, query: str, scfg: dict, timeout: float) -> list[dict]:
    """timelimit 창에서 0건이면 fallback_timelimit 창으로 1회 재시도."""
    limits = [scfg.get("timelimit", "m")]
    fallback = scfg.get("fallback_timelimit", "y")
    if fallback and fallback != limits[0]:
        limits.append(fallback)
    last_exc: Exception | None = None
    for limit in limits:
        try:
            with _ddgs()(timeout=int(timeout)) as ddgs:
                hits = list(getattr(ddgs, kind)(query, max_results=int(scfg.get("max_results", 4)), timelimit=limit))
        except Exception as exc:  # ddgs raises on empty result sets
            if "no results" not in str(exc).lower():
                raise
            last_exc, hits = exc, []
        if hits:
            return hits
    if last_exc:
        raise last_exc
    return []


def fetch_web(lq: LensQuery, scfg: dict, timeout: float) -> list[Row]:
    hits = _ddgs_search("text", lq.query, scfg, timeout)
    return [
        _row(lq, title=h.get("title", ""), url=h.get("href") or h.get("url", ""), snippet=h.get("body", ""))
        for h in hits
        if h.get("href") or h.get("url")
    ]


def fetch_news(lq: LensQuery, scfg: dict, timeout: float) -> list[Row]:
    hits = _ddgs_search("news", lq.query, scfg, timeout)
    return [
        _row(
            lq,
            title=h.get("title", ""),
            url=h.get("url") or h.get("href", ""),
            snippet=h.get("body", ""),
            published=h.get("date", ""),
            meta={"publisher": h.get("source", "")},
        )
        for h in hits
        if h.get("url") or h.get("href")
    ]


def fetch_github(lq: LensQuery, scfg: dict, timeout: float) -> list[Row]:
    since = (date.today() - timedelta(days=180)).isoformat()
    q = f"{lq.query} pushed:>{since} stars:>={int(scfg.get('min_stars', 20))}"
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": q, "sort": "stars", "order": "desc", "per_page": int(scfg.get("max_results", 5))}
    )
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.loads(_http_get(url, timeout, headers))
    rows = []
    for item in data.get("items") or []:
        rows.append(
            _row(
                lq,
                title=item.get("full_name", ""),
                url=item.get("html_url", ""),
                snippet=item.get("description") or "",
                published=item.get("pushed_at", ""),
                meta={
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language") or "",
                    "topics": item.get("topics") or [],
                },
            )
        )
    return rows


def fetch_arxiv(lq: LensQuery, scfg: dict, timeout: float) -> list[Row]:
    terms = " AND ".join(f'all:"{t}"' if " " in t else f"all:{t}" for t in lq.query.split(" ") if t)
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {
            "search_query": terms,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": int(scfg.get("max_results", 4)),
        }
    )
    root = ET.fromstring(_http_get(url, timeout))
    rows = []
    for entry in root.findall(f"{_ATOM}entry"):
        title = " ".join((entry.findtext(f"{_ATOM}title") or "").split())
        link = entry.findtext(f"{_ATOM}id") or ""
        summary = " ".join((entry.findtext(f"{_ATOM}summary") or "").split())
        rows.append(_row(lq, title=title, url=link, snippet=summary, published=entry.findtext(f"{_ATOM}published") or ""))
    return rows


def fetch_hn(lq: LensQuery, scfg: dict, timeout: float) -> list[Row]:
    url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
        {
            "query": lq.query,
            "tags": "story",
            "numericFilters": f"points>{int(scfg.get('min_points', 5))}",
            "hitsPerPage": int(scfg.get("max_results", 4)),
        }
    )
    data = json.loads(_http_get(url, timeout))
    rows = []
    for hit in data.get("hits") or []:
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        rows.append(
            _row(
                lq,
                title=hit.get("title", ""),
                url=link,
                snippet=f"Hacker News {hit.get('points', 0)} points · {hit.get('num_comments', 0)} comments",
                published=hit.get("created_at", ""),
                meta={"points": hit.get("points", 0)},
            )
        )
    return rows


FETCHERS: dict[str, Callable[[LensQuery, dict, float], list[Row]]] = {
    "web": fetch_web,
    "news": fetch_news,
    "github": fetch_github,
    "arxiv": fetch_arxiv,
    "hn": fetch_hn,
}


def load_fixture(path: Path) -> list[Row]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("results") if isinstance(data, dict) else data
    return [dict(r, meta=r.get("meta") or {}) for r in rows or []]


def fetch_all(queries: list[LensQuery], cfg: dict | None = None) -> tuple[list[Row], list[str]]:
    """병렬 수집. (rows, errors) — 한 소스 실패가 전체를 막지 않는다."""
    cfg = cfg or load_config()
    scfg_all = cfg.get("sources") or {}
    timeout = float(scfg_all.get("timeout_seconds", 12))
    workers = int(scfg_all.get("workers", 6))
    rows: list[Row] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(queries) or 1))) as pool:
        futures = {
            pool.submit(FETCHERS[lq.source], lq, scfg_all.get(lq.source) or {}, timeout): lq
            for lq in queries
            if lq.source in FETCHERS
        }
        for fut in as_completed(futures):
            lq = futures[fut]
            try:
                rows.extend(fut.result())
            except Exception as exc:  # noqa: BLE001 — 소스별 격리
                msg = f"{lq.source}:{lq.lens}:{lq.query[:40]} → {type(exc).__name__}: {str(exc)[:80]}"
                errors.append(msg)
                print(f"warn: {msg}", file=sys.stderr)
    return rows, errors
