"""Wiki Seed — Brief Graph → concepts (결정적, LLM 없음)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from lib.brief_graph import load_brief_graph
from lib.common import compress_sentences, studio_today, truncate

WORKDIR = Path.home() / "hermes-content-studio"
WIKI_ROOT = WORKDIR / "content" / "wiki"
CONCEPTS_DIR = WIKI_ROOT / "concepts"
INDEX_PATH = WIKI_ROOT / "index.md"
LOG_PATH = WIKI_ROOT / "log.md"


def _slug_safe(key: str) -> str:
    s = re.sub(r"[^\w\-가-힣]", "_", key.strip().lower())
    return s[:64] or "general"


def _group_nodes(graph: dict) -> dict[str, list[dict]]:
    by_key: dict[str, list[dict]] = {}
    for node in graph.get("nodes", []):
        key = _slug_safe(node.get("topic_key", "general"))
        by_key.setdefault(key, []).append(node)
    for key, group in by_key.items():
        group.sort(key=lambda n: n.get("stamp", ""), reverse=True)
    return by_key


def _streak_for(graph: dict, topic_key: str) -> int:
    for streak in graph.get("streaks", []):
        if _slug_safe(streak.get("topic_key", "")) == topic_key:
            return int(streak.get("streak_days", 0))
    return 0


def _write_concept(topic_key: str, nodes: list[dict], streak_days: int) -> Path:
    CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)
    latest = nodes[0]
    title = latest.get("title", topic_key)
    summary_src = title
    summary = compress_sentences(summary_src, max_chars=280) or truncate(summary_src, 200)

    sources: list[str] = []
    seen_urls: set[str] = set()
    for n in nodes[:5]:
        url = n.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append(f"- {n.get('stamp', '')}: [{truncate(n.get('title', ''), 80)}]({url})")

    related_links = ""

    today = studio_today()
    body = f"""---
topic_key: {topic_key}
updated_at: {today}
source_count: {len(nodes)}
streak_days: {streak_days}
---

# {truncate(title, 120)}

## 최신 요약
{summary}

## 출처
{chr(10).join(sources) if sources else "- (brief graph 노드 없음)"}

## 관련
{related_links or "—"}
"""
    path = CONCEPTS_DIR / f"{topic_key}.md"
    path.write_text(body.strip() + "\n", encoding="utf-8")
    return path


def _related_keys(by_key: dict[str, list[dict]], topic_key: str) -> str:
    others = sorted(k for k in by_key if k != topic_key)[:4]
    return " · ".join(f"[[{k}]]" for k in others) if others else "—"


def _rebuild_index(by_key: dict[str, list[dict]], graph: dict) -> None:
    rows = ["| topic_key | 요약 | 갱신 |", "|-----------|------|------|"]
    for key in sorted(by_key.keys()):
        nodes = by_key[key]
        latest = nodes[0]
        summ = truncate(latest.get("title", key), 60)
        streak = _streak_for(graph, key)
        rows.append(f"| {key} | {summ} | {latest.get('stamp', '')} (streak {streak}d) |")

    header = """# Hermes Studio Wiki — Index

> LLM Query 시 **1순위** 카탈로그. `HERMES_WIKI_SEED=1`로 Brief Graph에서 갱신.  
> 전략: `docs/LLM-WIKI-INTEGRATION.md`

## Concepts

"""
    entities = """
## Entities

| 엔티티 | 요약 | 갱신 |
|--------|------|------|
| — | Ingest 대기 | — |

## Sources (raw)

- `content/research/raw/` — 불변 클립·PDF·메모

## Output

- `content/wiki/output/` — `/ask` · 비교 분석 아카이브
"""
    WIKI_ROOT.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(header + "\n".join(rows) + "\n" + entities, encoding="utf-8")


def _append_log(label: str, detail: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"\n## [{stamp}] seed | {label}\n\n{detail}\n"
    if LOG_PATH.exists():
        LOG_PATH.write_text(LOG_PATH.read_text(encoding="utf-8") + entry, encoding="utf-8")
    else:
        LOG_PATH.write_text("# Wiki Log\n" + entry, encoding="utf-8")


def seed_from_brief_graph() -> dict:
    """Deterministic sync: brief_graph nodes → wiki/concepts + index."""
    graph = load_brief_graph()
    by_key = _group_nodes(graph)
    if not by_key:
        return {"concepts": 0, "message": "brief_graph 노드 없음"}

    written: list[str] = []
    for key, nodes in by_key.items():
        streak = _streak_for(graph, key)
        path = CONCEPTS_DIR / f"{key}.md"
        _write_concept(key, nodes, streak)
        # inject cross-links after all keys known
        written.append(key)
    for key in written:
        path = CONCEPTS_DIR / f"{key}.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        rel = _related_keys(by_key, key)
        text = re.sub(
            r"(## 관련\n).*$",
            rf"\1{rel}",
            text,
            flags=re.M,
        )
        path.write_text(text, encoding="utf-8")

    _rebuild_index(by_key, graph)
    _append_log(
        f"{len(written)} concepts",
        ", ".join(written[:12]) + ("…" if len(written) > 12 else ""),
    )
    return {"concepts": len(written), "keys": written, "index": str(INDEX_PATH)}


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    result = seed_from_brief_graph()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("concepts", 0) > 0 else 1)
