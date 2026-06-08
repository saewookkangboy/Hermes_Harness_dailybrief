"""Memory Router — Brief · packages · personal · Notion state 우선 질의."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from lib.brief_gate import brief_path
from lib.brief_graph import load_brief_graph
from lib.common import studio_today, truncate

WORKDIR = Path.home() / "hermes-content-studio"
PACKAGES = WORKDIR / "content" / "packages"
PERSONAL = WORKDIR / "content" / "personal"
STATE_PATH = WORKDIR / "content" / ".notion-archive-state.json"


@dataclass
class MemoryHit:
    source: str
    path: str
    snippet: str
    score: float = 0.0


@dataclass
class RouteResult:
    query: str
    stamp: str
    hits: list[MemoryHit] = field(default_factory=list)
    skip_web_search: bool = False
    answer: str = ""

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "stamp": self.stamp,
            "hit_count": len(self.hits),
            "skip_web_search": self.skip_web_search,
            "sources": [h.source for h in self.hits],
            "answer": self.answer,
        }


def _tokenize(query: str) -> list[str]:
    q = query.lower()
    tokens = re.findall(r"[a-z0-9가-힣]{2,}", q)
    return tokens[:12]


def _score_text(text: str, tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    tl = text.lower()
    return sum(1.0 for t in tokens if t in tl) / len(tokens)


def _read_snippet(path: Path, tokens: list[str], max_chars: int = 400) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not tokens:
        return truncate(text, max_chars)
    best = ""
    best_score = -1.0
    for block in re.split(r"\n{2,}", text):
        sc = _score_text(block, tokens)
        if sc > best_score:
            best_score = sc
            best = block
    if best_score <= 0:
        return truncate(text, max_chars)
    return truncate(best.strip(), max_chars)


def _list_brief_stamps(days: int = 14) -> list[str]:
    research = WORKDIR / "content" / "research"
    if not research.is_dir():
        return []
    stamps: list[str] = []
    for path in research.glob("*_brief.md"):
        stamp = path.name.replace("_brief.md", "")
        if re.match(r"^\d{4}-\d{2}-\d{2}$", stamp) and "SEED" not in stamp:
            stamps.append(stamp)
    stamps.sort(reverse=True)
    return stamps[:days]


def _search_brief(stamp: str, tokens: list[str]) -> MemoryHit | None:
    path = brief_path(stamp)
    if not path.exists():
        return None
    snip = _read_snippet(path, tokens)
    sc = _score_text(path.read_text(encoding="utf-8", errors="replace")[:8000], tokens)
    if sc <= 0 and tokens:
        sc = 0.3
    return MemoryHit("brief", str(path.relative_to(WORKDIR)), snip, sc)


def _search_packages(stamp: str, tokens: list[str]) -> list[MemoryHit]:
    hits: list[MemoryHit] = []
    if not PACKAGES.is_dir():
        return hits
    for path in sorted(PACKAGES.glob(f"{stamp}_*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        sc = _score_text(text, tokens)
        if sc > 0 or not tokens:
            hits.append(
                MemoryHit(
                    "packages",
                    str(path.relative_to(WORKDIR)),
                    _read_snippet(path, tokens),
                    sc or 0.2,
                )
            )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:4]


def _search_personal(tokens: list[str]) -> list[MemoryHit]:
    hits: list[MemoryHit] = []
    if not PERSONAL.is_dir():
        return hits
    for path in sorted(PERSONAL.glob("*.md"), reverse=True):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        sc = _score_text(text, tokens)
        if sc > 0:
            hits.append(
                MemoryHit(
                    "personal",
                    str(path.relative_to(WORKDIR)),
                    _read_snippet(path, tokens),
                    sc,
                )
            )
    return hits[:3]


def _search_brief_history(tokens: list[str], days: int = 14) -> list[MemoryHit]:
    hits: list[MemoryHit] = []
    for stamp in _list_brief_stamps(days):
        hit = _search_brief(stamp, tokens)
        if hit and hit.score >= 0.25:
            hits.append(hit)
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:5]


def _search_brief_graph(tokens: list[str], days: int = 14) -> list[MemoryHit]:
    if not tokens:
        return []
    graph = load_brief_graph()
    hits: list[MemoryHit] = []
    seen: set[str] = set()
    for streak in graph.get("streaks", []):
        blob = f"{streak.get('topic_key', '')} {streak.get('latest_title', '')}"
        sc = _score_text(blob, tokens)
        if sc <= 0:
            continue
        key = streak.get("topic_key", "")
        if key in seen:
            continue
        seen.add(key)
        dates = ", ".join(streak.get("dates", [])[:3])
        snip = (
            f"topic: {key}\n"
            f"연속 {streak.get('streak_days', 0)}일 · 등장 {streak.get('appearances', 0)}회\n"
            f"최신: {streak.get('latest_title', '')}\n"
            f"dates: {dates}"
        )
        hits.append(MemoryHit("brief_graph", f"graph/{key}", snip, sc + 0.1))
    for node in graph.get("nodes", []):
        title = node.get("title", "")
        sc = _score_text(title, tokens)
        if sc < 0.35:
            continue
        nk = f"{node.get('stamp')}/{node.get('topic_key')}"
        if nk in seen:
            continue
        seen.add(nk)
        hits.append(
            MemoryHit(
                "brief_graph",
                f"graph/{node.get('stamp')}/{node.get('topic_key')}",
                f"{node.get('stamp')}: {title}",
                sc,
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:4]


def _search_notion_state(stamp: str) -> MemoryHit | None:
    if not STATE_PATH.exists():
        return None
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    day = (state.get("days") or {}).get(stamp)
    if not day:
        return None
    url = day.get("url", "") if isinstance(day, dict) else ""
    pages = []
    prefix = f"{stamp}/"
    for key, meta in (state.get("pages") or {}).items():
        if key.startswith(prefix) and isinstance(meta, dict):
            pages.append(f"{key.split('/')[-1]}: {meta.get('url', '')}")
    snip = f"Daily: {url}\n" + "\n".join(pages[:5])
    return MemoryHit("notion_state", str(STATE_PATH.relative_to(WORKDIR)), snip, 0.5)


def route_query(query: str, stamp: str | None = None, *, graph_days: int = 14) -> RouteResult:
    stamp = stamp or studio_today()
    tokens = _tokenize(query)
    result = RouteResult(query=query, stamp=stamp)

    brief_hit = _search_brief(stamp, tokens)
    if brief_hit and brief_hit.score >= 0.2:
        result.hits.append(brief_hit)
    else:
        result.hits.extend(_search_brief_history(tokens, graph_days))

    result.hits.extend(_search_brief_graph(tokens, graph_days))
    result.hits.extend(_search_packages(stamp, tokens))
    result.hits.extend(_search_personal(tokens))

    notion_hit = _search_notion_state(stamp)
    if notion_hit:
        result.hits.append(notion_hit)

    # dedupe by path
    seen_paths: set[str] = set()
    deduped: list[MemoryHit] = []
    for h in sorted(result.hits, key=lambda x: x.score, reverse=True):
        if h.path in seen_paths:
            continue
        seen_paths.add(h.path)
        deduped.append(h)
    result.hits = deduped

    result.skip_web_search = len(result.hits) > 0 and any(h.score >= 0.2 for h in result.hits)
    result.answer = format_answer(result)
    return result


def format_answer(result: RouteResult) -> str:
    if not result.hits:
        return (
            f"로컬 메모리에 '{result.query}' 관련 히트 없음.\n"
            "web_search 또는 run-research-brief.sh 권장."
        )
    lines = [
        f"🧠 Memory Router · {result.stamp}",
        f"질의: {result.query}",
        f"web_search 생략: {'예' if result.skip_web_search else '아니오'}",
        "",
    ]
    graph_hits = [h for h in result.hits if h.source == "brief_graph"]
    other_hits = [h for h in result.hits if h.source != "brief_graph"]
    if graph_hits:
        lines.append("### Brief Graph 매칭")
        for h in graph_hits[:3]:
            lines.extend([f"- `{h.path}` (score {h.score:.2f})", h.snippet, ""])
    for h in other_hits[:5]:
        lines.extend(
            [
                f"### [{h.source}] `{h.path}` (score {h.score:.2f})",
                h.snippet,
                "",
            ]
        )
    return "\n".join(lines).strip()


def brief_top3(stamp: str | None = None) -> str:
    stamp = stamp or studio_today()
    path = brief_path(stamp)
    if not path.exists():
        return f"⚠️ {stamp} brief 없음"
    text = path.read_text(encoding="utf-8")
    titles = re.findall(r"^### \d+\.\s+(.+)$", text, re.M)[:3]
    summaries = re.findall(r"^\*\*한국어 요약:\*\*\s*(.+)$", text, re.M)[:3]
    lines = [f"☀️ Top 3 · {stamp}", ""]
    for i, title in enumerate(titles, 1):
        summ = summaries[i - 1] if i <= len(summaries) else ""
        lines.append(f"{i}. **{title}**")
        if summ:
            lines.append(f"   {truncate(summ, 120)}")
    return "\n".join(lines)


def recent_briefs(days: int = 3) -> str:
    if not (WORKDIR / "content" / "research").is_dir():
        return "brief 없음"
    paths = sorted(
        (WORKDIR / "content" / "research").glob("*_brief.md"),
        reverse=True,
    )[:days]
    lines = [f"📅 최근 Brief ({len(paths)}일)", ""]
    for p in paths:
        stamp = p.name.replace("_brief.md", "")
        n = len(re.findall(r"^### \d+\.", p.read_text(encoding="utf-8"), re.M))
        lines.append(f"• {stamp} — Top {n} · `{p.relative_to(WORKDIR)}`")
    return "\n".join(lines)
