#!/usr/bin/env python3
"""일일 웹 검색 사전 수집 — Brief SoT 입력 (_search_context_{date}.json).

- config/research-brief.yaml 쿼리 + {year}/{ymd} 템플릿
- timelimit=week 로 최신 결과 우선
- 실패 쿼리 1회 재시도
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

WORKDIR = Path.home() / "hermes-content-studio"
OUTPUT_DIR = WORKDIR / "content" / "research"
HARNESS_CONFIG = WORKDIR / "config" / "harness.yaml"
BRIEF_CONFIG = WORKDIR / "config" / "research-brief.yaml"

DEFAULT_QUERIES = [
    "OpenAI ChatGPT update {year} business marketing",
    "Anthropic Claude update {year} enterprise",
    "Google Gemini update {year} marketing",
    "Perplexity AI search update {year}",
    "Korea AX AI transformation news {year}",
    "South Korea enterprise AI adoption {year}",
    "AI governance responsible AI enterprise {year}",
    "AI literacy marketing team training {year}",
    "AI agent marketing automation github {year}",
    "prompt engineering context engineering harness {year}",
    "Hermes agent NousResearch open source {year}",
    "AI agent use case enterprise workflow {year}",
    "AEO answer engine optimization {year}",
    "digital marketing Korea AX transformation {year}",
]


def _load_brief_config() -> dict:
    try:
        import yaml  # type: ignore

        if BRIEF_CONFIG.exists():
            return yaml.safe_load(BRIEF_CONFIG.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        pass
    return {}


def expand_query(template: str, today: date) -> str:
    return (
        template.replace("{year}", str(today.year))
        .replace("{ymd}", today.isoformat())
        .replace("{month}", f"{today.month:02d}")
    )


def _load_queries(today: date) -> list[str]:
    cfg = _load_brief_config()
    raw = cfg.get("search_queries") or DEFAULT_QUERIES
    queries = [expand_query(str(q), today) for q in raw]
    extra = (os.environ.get("HERMES_RESEARCH_KEYWORDS") or "").strip()
    if extra:
        # Treat as one or more queries separated by | or newlines
        parts = [p.strip() for p in re.split(r"[|\n]+", extra) if p.strip()]
        # Prefer keyword queries first
        queries = parts + [q for q in queries if q not in parts]
    keyword_only = (os.environ.get("HERMES_RESEARCH_KEYWORD_ONLY") or "").strip() in (
        "1",
        "true",
        "True",
    )
    if keyword_only and extra:
        parts = [p.strip() for p in re.split(r"[|\n]+", extra) if p.strip()]
        return parts or queries
    return queries


def _min_results() -> int:
    cfg = _load_brief_config()
    freshness = cfg.get("freshness") or {}
    return int(freshness.get("min_search_results", 7))


def _timelimit() -> str:
    cfg = _load_brief_config()
    freshness = cfg.get("freshness") or {}
    return str(freshness.get("search_timelimit", "w"))


def _harness_workers() -> int:
    try:
        import yaml  # type: ignore

        if HARNESS_CONFIG.exists():
            cfg = yaml.safe_load(HARNESS_CONFIG.read_text(encoding="utf-8")) or {}
            return int((cfg.get("performance") or {}).get("parallel_search_workers", 4))
    except Exception:  # noqa: BLE001
        pass
    return 4


def _harness_max_results() -> int:
    try:
        import yaml  # type: ignore

        if HARNESS_CONFIG.exists():
            cfg = yaml.safe_load(HARNESS_CONFIG.read_text(encoding="utf-8")) or {}
            return int((cfg.get("performance") or {}).get("search_max_results", 3))
    except Exception:  # noqa: BLE001
        pass
    return 3


def _import_ddgs():
    try:
        from ddgs import DDGS  # type: ignore
        return DDGS
    except ImportError:
        venv_py = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"
        if venv_py.exists():
            print(f"ddgs not found — install: {venv_py} -m pip install ddgs", file=sys.stderr)
        raise


def _search_query(query: str, max_results: int, timelimit: str) -> list[dict]:
    DDGS = _import_ddgs()
    rows: list[dict] = []
    for attempt in range(2):
        try:
            with DDGS() as ddgs:
                hits = list(
                    ddgs.text(query, max_results=max_results, timelimit=timelimit)
                )
            break
        except TypeError:
            try:
                with DDGS() as ddgs:
                    hits = list(ddgs.text(query, max_results=max_results))
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 1:
                    print(f"warn: search failed for {query!r}: {exc}", file=sys.stderr)
                    return rows
                time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001
            if attempt == 1:
                print(f"warn: search failed for {query!r}: {exc}", file=sys.stderr)
                return rows
            time.sleep(0.5)
    else:
        return rows

    for hit in hits:
        url = (hit.get("href") or hit.get("url") or "").strip()
        if not url:
            continue
        rows.append(
            {
                "query": query,
                "title": (hit.get("title") or "").strip(),
                "url": url,
                "snippet": (hit.get("body") or hit.get("snippet") or "").strip()[:400],
            }
        )
    return rows


def search_all(queries: list[str], max_results: int = 3, workers: int = 4, timelimit: str = "w") -> list[dict]:
    seen_urls: set[str] = set()
    results: list[dict] = []
    worker_count = min(workers, max(1, len(queries)))

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {
            pool.submit(_search_query, query, max_results, timelimit): query
            for query in queries
        }
        for future in as_completed(futures):
            for row in future.result():
                url = row["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(row)
    return results


def to_markdown(results: list[dict], start: date, end: date) -> str:
    lines = [
        f"# 수집된 웹 검색 결과 ({start} ~ {end})",
        "",
        f"총 {len(results)}건 — Brief SoT 입력 · Hermes write_file용",
        "",
    ]
    for i, r in enumerate(results, 1):
        lines.extend(
            [
                f"## {i}. {r['title'] or '(제목 없음)'}",
                f"- **검색어:** {r['query']}",
                f"- **URL:** {r['url']}",
                f"- **요약:** {r['snippet'] or '(없음)'}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    stamp = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    today = date.fromisoformat(stamp)
    queries = _load_queries(today)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"_search_context_{stamp}.json"
    md_path = OUTPUT_DIR / f"_search_context_{stamp}.md"

    workers = _harness_workers()
    max_results = _harness_max_results()
    timelimit = _timelimit()
    min_results = _min_results()

    results = search_all(queries, max_results=max_results, workers=workers, timelimit=timelimit)
    if len(results) < min_results:
        print(
            f"warn: {len(results)} results (< {min_results}) — max_results bump retry",
            file=sys.stderr,
        )
        results = search_all(
            queries,
            max_results=max_results + 2,
            workers=workers,
            timelimit=timelimit,
        )

    if len(results) < min_results:
        print(
            f"warn: only {len(results)} results after retry — continuing anyway",
            file=sys.stderr,
        )

    payload = {
        "date": stamp,
        "period_start": today.isoformat(),
        "period_end": today.isoformat(),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "timelimit": timelimit,
        "query_count": len(queries),
        "count": len(results),
        "results": results,
        "keywords": (os.environ.get("HERMES_RESEARCH_KEYWORDS") or "").strip(),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(results, today, today), encoding="utf-8")

    print(json_path)
    print(md_path)
    print(f"Collected {len(results)} search hits ({len(queries)} queries, timelimit={timelimit})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
