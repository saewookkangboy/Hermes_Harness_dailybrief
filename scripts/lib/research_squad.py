"""Research Squad — Scout · Analyst · Curator · Archivist (결정적 멀티 역할)."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.brief_gate import load_search_context
from lib.brief_quality import classify_insight, synthesize_marketer_view
from lib.common import slugify, studio_today, truncate
from lib.harness import timed_stage
from lib.memory_router import route_query
from lib.personal_bridge import format_inbox_summary, queue_topic_for_brief, sync_inbox_from_personal
from lib.wiki_router import route_wiki

WORKDIR = Path.home() / "hermes-content-studio"
RAW_DIR = WORKDIR / "content" / "research" / "raw"
HANDOFF_DIR = WORKDIR / ".harness" / "handoffs"


@dataclass
class SquadRole:
    role: str
    status: str
    output: str = ""
    artifacts: list[str] = field(default_factory=list)


@dataclass
class SquadReport:
    topic: str
    stamp: str
    roles: list[SquadRole] = field(default_factory=list)
    elapsed_seconds: float = 0.0


def _tokenize(topic: str) -> list[str]:
    return re.findall(r"[a-z0-9가-힣]{2,}", topic.lower())[:12]


def _scout(topic: str, stamp: str) -> SquadRole:
    tokens = _tokenize(topic)
    ctx = load_search_context(stamp) or {}
    results = ctx.get("results") or []
    hits: list[dict] = []
    for row in results:
        blob = f"{row.get('title', '')} {row.get('snippet', '')} {row.get('query', '')}".lower()
        score = sum(1 for t in tokens if t in blob) / max(len(tokens), 1)
        if score >= 0.2:
            hits.append({**row, "_score": round(score, 2)})
    hits.sort(key=lambda h: h.get("_score", 0), reverse=True)
    hits = hits[:5]

    lines = [f"## Scout — 검색 컨텍스트 ({len(hits)}건)", ""]
    for i, h in enumerate(hits, 1):
        lines.append(f"{i}. **{truncate(h.get('title', ''), 70)}**")
        lines.append(f"   - {truncate(h.get('snippet', ''), 120)}")
        if h.get("url"):
            lines.append(f"   - {h['url']}")
        lines.append("")
    if not hits:
        lines.append("_search_context에 매칭 없음 — run-research-brief.sh 권장_")
    return SquadRole("scout", "PASS" if hits else "WARN", "\n".join(lines), artifacts=[])


def _analyst(topic: str, stamp: str, scout: SquadRole) -> SquadRole:
    tokens = _tokenize(topic)
    title = topic
    snippet = scout.output[:300] if scout.output else topic
    query = " ".join(tokens[:3])
    topic_key = classify_insight(title, snippet, query)
    view = synthesize_marketer_view(topic_key, title, channel="blog")
    memory = route_query(topic, stamp)

    lines = [
        f"## Analyst — SCQA · 마케터 뷰",
        "",
        f"- **topic_key:** `{topic_key}`",
        f"- **마케터 관점:** {view}",
        "",
        "### Memory Router",
        memory.answer[:600] if memory.answer else "(히트 없음)",
    ]
    return SquadRole("analyst", "PASS", "\n".join(lines))


def _curator(topic: str, stamp: str) -> SquadRole:
    sync_inbox_from_personal(stamp)
    queue_topic_for_brief(topic, source="research-squad")
    wiki_hits = route_wiki(topic)
    inbox = format_inbox_summary()

    lines = [
        "## Curator — Brief 큐 · Wiki",
        "",
        inbox,
        "",
        "### Wiki hits",
    ]
    if wiki_hits:
        for h in wiki_hits[:3]:
            lines.append(f"- `{h.path}` — {truncate(h.snippet, 80)}")
    else:
        lines.append("- (wiki concept 없음 — `hermes-agent.sh wiki seed`)")
    return SquadRole("curator", "PASS", "\n".join(lines))


def _archivist(topic: str, stamp: str, roles: list[SquadRole]) -> SquadRole:
    slug = slugify(topic)[:40] or "topic"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{stamp}_squad_{slug}.md"
    body = "\n\n".join(r.output for r in roles if r.output)
    doc = f"""# Research Squad — {topic}

**날짜:** {stamp}
**역할:** Scout → Analyst → Curator → Archivist

{body}

---
> 다음: `run-research-brief.sh` 또는 `telegram-custom.sh` 심층 리서치
"""
    path.write_text(doc.strip() + "\n", encoding="utf-8")
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    handoff = HANDOFF_DIR / f"{stamp}_research-squad_{slug}.json"
    handoff.write_text(
        json.dumps(
            {
                "topic": topic,
                "stamp": stamp,
                "raw_path": str(path),
                "roles": [r.role for r in roles],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return SquadRole("archivist", "PASS", f"저장: `{path.relative_to(WORKDIR)}`", artifacts=[str(path), str(handoff)])


def run_research_squad(topic: str, stamp: str | None = None) -> SquadReport:
    stamp = stamp or studio_today()
    t0 = time.perf_counter()
    report = SquadReport(topic=topic, stamp=stamp)

    with timed_stage("research_squad"):
        scout = _scout(topic, stamp)
        report.roles.append(scout)
        analyst = _analyst(topic, stamp, scout)
        report.roles.append(analyst)
        curator = _curator(topic, stamp)
        report.roles.append(curator)
        archivist = _archivist(topic, stamp, report.roles)
        report.roles.append(archivist)

    report.elapsed_seconds = round(time.perf_counter() - t0, 2)
    return report


def format_squad_report(report: SquadReport) -> str:
    lines = [
        f"🔬 Research Squad · {report.topic}",
        f"📅 {report.stamp} · ⏱ {report.elapsed_seconds}s",
        "",
    ]
    for role in report.roles:
        sym = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(role.status, "·")
        lines.append(f"### {sym} {role.role.title()}")
        lines.append(role.output)
        lines.append("")
    return "\n".join(lines).rstrip()
