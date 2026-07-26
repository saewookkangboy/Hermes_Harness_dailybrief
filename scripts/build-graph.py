#!/usr/bin/env python3
"""브리프 → 그래프 결정적 추출. LLM 0회.

사용:
  python3 scripts/build-graph.py --rebuild
  python3 scripts/build-graph.py --since 2026-07-01
  python3 scripts/build-graph.py --brief content/research/2026-07-20_brief.md
  python3 scripts/build-graph.py --ctor
  python3 scripts/build-graph.py --dry-run --rebuild
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import graph as G  # noqa: E402
from lib import ledger  # noqa: E402

STUDIO = ledger.STUDIO
RESEARCH = STUDIO / "content" / "research"
WIKI = STUDIO / "content" / "wiki"

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
URL_RE = re.compile(r"https?://[^\s)\]>\"']+")
HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$", re.MULTILINE)
BOLD_RE = re.compile(r"\*\*([^*\n]{2,40})\*\*")
NUMERIC_CLAIM_RE = re.compile(
    r"[^.\n]*?\d+(?:[.,]\d+)?\s*(?:%|퍼센트|배|억|만|천|원|달러|건|명|개)[^.\n]*[.]?"
)

STOP_HEADINGS = {"목차", "출처", "참고", "요약", "tldr", "tl;dr", "references"}


def brief_date(path: Path) -> str:
    m = DATE_RE.search(path.name)
    return m.group(1) if m else "1970-01-01"


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2]
    return text


def extract_concepts(body: str) -> list[str]:
    out: list[str] = []
    for _, title in HEADING_RE.findall(body):
        t = re.sub(r"[#*`\[\]]", "", title).strip()
        if t and t.lower() not in STOP_HEADINGS and 2 <= len(t) <= 60:
            out.append(t)
    for term in BOLD_RE.findall(body):
        t = term.strip()
        if 2 <= len(t) <= 40:
            out.append(t)
    seen, uniq = set(), []
    for t in out:
        k = G.slug(t)
        if k and k not in seen:
            seen.add(k)
            uniq.append(t)
    return uniq


def extract_source_claims(body: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for block in re.split(r"\n\s*\n", body):
        urls = URL_RE.findall(block)
        if not urls:
            continue
        claims = [c.strip() for c in NUMERIC_CLAIM_RE.findall(block) if len(c.strip()) > 15]
        if not claims:
            plain = re.sub(r"\s+", " ", URL_RE.sub("", block)).strip()
            if len(plain) > 20:
                claims = [plain[:200]]
        for u in urls[:3]:
            for c in claims[:3]:
                pairs.append((u.rstrip(".,)"), c))
    return pairs


def detect_superseded(con, body: str, date: str) -> list[tuple[str, str]]:
    superseded: list[tuple[str, str]] = []
    concepts = [G.slug(c) for c in extract_concepts(body)]
    if not concepts:
        return superseded

    new_numbers = set(re.findall(r"\d+(?:[.,]\d+)?\s*(?:%|배|억|만)", body))
    if not new_numbers:
        return superseded

    ph = ",".join("?" * len(concepts))
    rows = con.execute(
        f"""
        SELECT DISTINCT c.id AS claim_id, c.digest
          FROM node c
          JOIN edge e ON e.src = c.id AND e.rel = 'mentions' AND e.valid_to IS NULL
         WHERE c.kind = 'claim'
           AND e.dst IN ({ph})
           AND c.first_seen < ?
        """,
        (*[f"concept:{c}" for c in concepts], date),
    ).fetchall()

    for r in rows:
        old_numbers = set(re.findall(r"\d+(?:[.,]\d+)?\s*(?:%|배|억|만)", r["digest"] or ""))
        if old_numbers and not (old_numbers & new_numbers):
            superseded.append((r["claim_id"], r["digest"] or ""))
    return superseded


def ingest_brief(con, path: Path, *, dry: bool = False) -> dict:
    date = brief_date(path)
    body = strip_frontmatter(path.read_text(encoding="utf-8"))
    rel_uri = str(path.relative_to(STUDIO))
    counts = {"concepts": 0, "claims": 0, "sources": 0, "invalidated": 0}

    concept_ids: list[str] = []
    for c in extract_concepts(body):
        nid = f"concept:{G.slug(c)}"
        concept_ids.append(nid)
        counts["concepts"] += 1
        if not dry:
            G.upsert_node(con, nid, "concept", c, seen=date)

    for url, claim in extract_source_claims(body):
        s_id = G.sid("source", url)
        k_id = G.sid("claim", claim)
        counts["sources"] += 1
        counts["claims"] += 1
        if dry:
            continue
        G.upsert_node(con, s_id, "source", url, body_uri=None, seen=date)
        G.upsert_node(
            con, k_id, "claim", claim[:120], digest=claim, body_uri=rel_uri, seen=date
        )
        G.add_edge(con, k_id, s_id, "cites", valid_from=date)
        for cid in concept_ids:
            G.add_edge(con, k_id, cid, "mentions", valid_from=date)

    if not dry:
        for claim_id, _ in detect_superseded(con, body, date):
            counts["invalidated"] += G.invalidate_claim(
                con, claim_id, by=f"brief:{date}", as_of=date
            )
    return counts


def ingest_assets(
    con,
    *,
    dry: bool = False,
    only_dates: set[str] | None = None,
) -> int:
    """발행물 노드 + derived_from.

    only_dates가 있으면 해당 날짜 파일만 처리 (증분 빌드).
    mentions 엣지는 날짜별로 1회 캐시.
    """
    n = 0
    mentions_cache: dict[str, list[str]] = {}

    def mentions_for(date: str) -> list[str]:
        if date not in mentions_cache:
            mentions_cache[date] = [
                row["dst"]
                for row in con.execute(
                    "SELECT dst FROM edge WHERE rel='mentions' AND valid_from=? "
                    "AND valid_to IS NULL",
                    (date,),
                ).fetchall()
            ]
        return mentions_cache[date]

    for ch in ("blog", "instagram", "linkedin", "newsletter", "lectures"):
        d = STUDIO / "content" / ch
        if not d.exists():
            continue
        for f in d.iterdir():
            if f.is_dir():
                continue
            m = re.match(r"(\d{4}-\d{2}-\d{2})_", f.name)
            if not m:
                continue
            date = m.group(1)
            if only_dates is not None and date not in only_dates:
                continue
            aid = f"asset:{f.stem}"
            n += 1
            if dry:
                continue
            # 이미 동일 body_uri로 존재하면 FTS/엣지 재작업 최소화
            existing = con.execute(
                "SELECT body_uri FROM node WHERE id = ?", (aid,)
            ).fetchone()
            rel = str(f.relative_to(STUDIO))
            # 증분: 이미 동일 URI면 스킵. rebuild(only_dates=None)는 전량 갱신.
            if only_dates is not None and existing and existing["body_uri"] == rel:
                continue
            G.upsert_node(con, aid, "asset", f.stem, body_uri=rel, seen=date)
            if (RESEARCH / f"{date}_brief.md").exists():
                for dst in mentions_for(date):
                    G.add_edge(con, aid, dst, "derived_from", valid_from=date)
    return n


def ingest_ctor(con, *, dry: bool = False) -> int:
    candidates = [
        STUDIO / ".harness" / "ctor-ledger.jsonl",
        STUDIO / "content" / "newsletter" / "ctor-ledger.jsonl",
    ]
    src = next((p for p in candidates if p.exists()), None)
    if not src:
        print(f"  (CTOR 원장 없음 — 건너뜀: {[str(c) for c in candidates]})")
        return 0

    n = 0
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        date = rec.get("date")
        delivered = rec.get("delivered") or 0
        opens = rec.get("opens") or 0
        clicks = rec.get("clicks") or 0
        if not date or not opens:
            continue
        ctor = clicks / opens
        aid = f"asset:{date}_newsletter"
        n += 1
        if dry:
            continue
        G.upsert_node(con, aid, "asset", f"{date}_newsletter", seen=date)
        for metric, value in (
            ("ctor", ctor),
            ("opens", opens),
            ("clicks", clicks),
            ("delivered", delivered),
        ):
            con.execute(
                """INSERT OR REPLACE INTO perf
                   (asset_id, metric, value, period, source)
                   VALUES (?,?,?,?,'ctor-ledger')""",
                (aid, metric, float(value), date),
            )
    return n


def emit_obsidian(con) -> int:
    out = WIKI / "concepts"
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for r in con.execute("SELECT * FROM node WHERE kind='concept'"):
        links = [
            f"[[{x['label']}]]"
            for x in G.walk(con, [r["id"]], hops=1)
            if x["kind"] == "concept" and x["id"] != r["id"]
        ][:12]
        (out / f"{G.slug(r['label'])}.md").write_text(
            f"---\nlabel: {r['label']}\nfirst_seen: {r['first_seen']}\n"
            f"last_seen: {r['last_seen']}\nmentions: {r['mention_cnt']}\n---\n\n"
            f"{r['digest'] or ''}\n\n## 연결\n"
            + "\n".join(f"- {l}" for l in links)
            + "\n",
            encoding="utf-8",
        )
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--since")
    ap.add_argument("--brief")
    ap.add_argument("--ctor", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--emit-md", action="store_true")
    a = ap.parse_args()

    con = G.connect()
    total = {"concepts": 0, "claims": 0, "sources": 0, "invalidated": 0}

    if a.brief:
        briefs = [Path(a.brief)]
    elif a.rebuild:
        briefs = sorted(RESEARCH.glob("*_brief.md"))
    elif a.since:
        briefs = [p for p in sorted(RESEARCH.glob("*_brief.md")) if brief_date(p) >= a.since]
    else:
        briefs = sorted(RESEARCH.glob("*_brief.md"))[-1:]

    for b in briefs:
        if not b.exists():
            print(f"  skip missing: {b}")
            continue
        c = ingest_brief(con, b, dry=a.dry_run)
        for k in total:
            total[k] += c[k]
        print(
            f"  {b.name}: concepts={c['concepts']} claims={c['claims']} "
            f"invalidated={c['invalidated']}"
        )

    # 증분: 처리한 브리프 날짜의 자산만. --rebuild 시 전체.
    if a.rebuild:
        only_dates = None
    else:
        only_dates = {brief_date(b) for b in briefs if b.exists()}
    assets = ingest_assets(con, dry=a.dry_run, only_dates=only_dates)
    ctor_rows = ingest_ctor(con, dry=a.dry_run) if (a.ctor or a.rebuild) else 0
    md_n = 0

    if not a.dry_run:
        if a.emit_md:
            md_n = emit_obsidian(con)
        G.meta_set(con, "last_build", G.now_iso())
        G.meta_set(con, "last_mode", "rebuild" if a.rebuild else "incremental")
        con.commit()
        st = G.stats(con)
        st["assets_scanned"] = assets
        st["ctor_rows"] = ctor_rows
        st["obsidian_md"] = md_n
        st["only_dates"] = sorted(only_dates) if only_dates is not None else "all"
        WIKI.mkdir(parents=True, exist_ok=True)
        (WIKI / "graph-stats.json").write_text(
            json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        ledger.append(
            ledger.CostEntry.now(
                "wiki_graph",
                deterministic=True,
                run_id="build-graph",
                note=f"briefs={len(briefs)} nodes={st['nodes']}",
            )
        )
        print(f"\n✓ {json.dumps(st, ensure_ascii=False)}")
    else:
        print(f"\n[dry-run] {total} assets={assets}")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
