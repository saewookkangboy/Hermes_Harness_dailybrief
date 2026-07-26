"""서브그래프 → LLM 컨텍스트 문자열. 예산 하드 캡 준수."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import graph as G  # noqa: E402
from lib.skill_loader import estimate_tokens  # noqa: E402


def _sources_for(con, claim_ids: list[str]) -> dict[str, list[str]]:
    """claim → source URL 목록 (live만)."""
    if not claim_ids:
        return {}
    ph = ",".join("?" * len(claim_ids))
    rows = con.execute(
        f"""
        SELECT e.src AS claim_id, n.label AS url
          FROM edge e JOIN node n ON n.id = e.dst
         WHERE e.rel = 'cites' AND e.valid_to IS NULL
           AND e.src IN ({ph}) AND n.kind = 'source'
        """,
        claim_ids,
    ).fetchall()
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["claim_id"], []).append(r["url"])
    return out


def _invalidation_notice(con, concept_ids: list[str]) -> list[str]:
    """무효화된 claim의 존재만 알린다. 내용은 넣지 않는다."""
    if not concept_ids:
        return []
    ph = ",".join("?" * len(concept_ids))
    rows = con.execute(
        f"""
        SELECT DISTINCT n.label AS concept, e.invalidated_by AS by, e.valid_to AS since
          FROM edge e
          JOIN node n ON n.id = e.dst AND n.kind = 'concept'
         WHERE e.rel = 'mentions' AND e.valid_to IS NOT NULL
           AND e.dst IN ({ph})
         ORDER BY e.valid_to DESC LIMIT 5
        """,
        concept_ids,
    ).fetchall()
    return [
        f"- {r['concept']}: 이전 수치가 {r['since']} 기준 무효화됨 (출처 {r['by']}). "
        f"오래된 값을 인용하지 말 것."
        for r in rows
    ]


def build(
    question: str,
    *,
    budget_tokens: int = 3000,
    hops: int = 2,
    seeds_n: int = 5,
) -> tuple[str, dict]:
    con = G.connect()
    seeds = G.search(con, question, limit=seeds_n)
    # 운영 질의 시드를 항상 병합 (채널·재활용·무효화)
    for sid in G.search_operational(con, question, limit=seeds_n):
        if sid not in seeds:
            seeds.append(sid)
        if len(seeds) >= seeds_n:
            break
    seeds = seeds[:seeds_n]
    if not seeds:
        con.close()
        return "", {"seeds": 0, "nodes": 0, "tokens": 0, "truncated": False}

    sub = G.walk(con, seeds, hops=hops, live_only=True)
    claims = [n for n in sub if n["kind"] == "claim"]
    concepts = [n for n in sub if n["kind"] == "concept"]
    assets = [n for n in sub if n["kind"] == "asset"]
    src_map = _sources_for(con, [c["id"] for c in claims])
    notices = _invalidation_notice(con, [c["id"] for c in concepts])

    parts: list[str] = ["# 관련 컨텍스트 (누적 위키 그래프)", ""]
    used = estimate_tokens("\n".join(parts))
    truncated = False

    def add(block: str) -> bool:
        nonlocal used, truncated
        t = estimate_tokens(block)
        if used + t > budget_tokens:
            truncated = True
            return False
        parts.append(block)
        used += t
        return True

    if concepts:
        add(
            "## 개념\n"
            + "\n".join(
                f"- **{c['label']}** (언급 {c['mention_cnt']}회, 최근 {c['last_seen']})"
                for c in concepts[:15]
            )
        )

    if claims:
        parts.append("\n## 근거 (출처 포함)")
        used += 4
        for c in claims:
            urls = src_map.get(c["id"], [])
            src = f"  출처: {urls[0]}" if urls else "  출처: (없음 — 인용 주의)"
            block = f"- {c['digest'] or c['label']}\n{src}"
            if not add(block):
                break

    if assets:
        add(
            "\n## 과거 발행물 (재활용 후보)\n"
            + "\n".join(f"- {a['label']} → `{a['body_uri']}`" for a in assets[:8])
        )

    if notices:
        add("\n## ⚠ 무효화 경고\n" + "\n".join(notices))

    con.close()
    text = "\n".join(parts)
    meta = {
        "seeds": len(seeds),
        "nodes": len(sub),
        "concepts": len(concepts),
        "claims": len(claims),
        "assets": len(assets),
        "tokens": estimate_tokens(text),
        "budget": budget_tokens,
        "truncated": truncated,
    }
    return text, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--budget", type=int, default=3000)
    ap.add_argument("--hops", type=int, default=2)
    ap.add_argument("--meta", action="store_true", help="메타만 JSON 출력")
    a = ap.parse_args()

    text, meta = build(a.question, budget_tokens=a.budget, hops=a.hops)
    if a.meta:
        print(json.dumps(meta, ensure_ascii=False))
    else:
        print(text)
        print(f"\n<!-- {json.dumps(meta, ensure_ascii=False)} -->", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
