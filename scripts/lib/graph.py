"""누적 개념 그래프 — upsert / invalidate / walk. stdlib only."""
from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from . import ledger

DB_PATH = ledger.STUDIO / "content" / "wiki" / "graph.db"
DDL_PATH = ledger.STUDIO / "schemas" / "graph.sql"


def slug(text: str) -> str:
    """한글 보존 슬러그. 영문은 소문자, 공백은 하이픈."""
    t = unicodedata.normalize("NFC", text).strip().lower()
    t = re.sub(r"[^\w가-힣]+", "-", t, flags=re.UNICODE)
    return re.sub(r"-{2,}", "-", t).strip("-")[:80]


def sid(prefix: str, text: str) -> str:
    return f"{prefix}:{hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    con.executescript(DDL_PATH.read_text(encoding="utf-8"))
    return con


def upsert_node(
    con,
    node_id: str,
    kind: str,
    label: str,
    *,
    body_uri: str | None = None,
    digest: str | None = None,
    seen: str,
) -> None:
    dig = (digest or "")[:200]
    prev = con.execute(
        "SELECT digest FROM node WHERE id = ?", (node_id,)
    ).fetchone()
    con.execute(
        """
        INSERT INTO node (id, kind, label, body_uri, digest,
                          first_seen, last_seen, mention_cnt)
        VALUES (?,?,?,?,?,?,?,1)
        ON CONFLICT(id) DO UPDATE SET
          last_seen   = CASE
                          WHEN excluded.last_seen > node.last_seen
                          THEN excluded.last_seen ELSE node.last_seen END,
          mention_cnt = node.mention_cnt + 1,
          digest      = COALESCE(excluded.digest, node.digest),
          body_uri    = COALESCE(excluded.body_uri, node.body_uri)
        """,
        (node_id, kind, label, body_uri, dig, seen, seen),
    )

    # FTS는 digest 변경·신규일 때만 갱신 (증분 빌드 병목 제거)
    if prev is None or (prev["digest"] or "") != dig:
        con.execute("DELETE FROM node_fts WHERE id = ?", (node_id,))
        con.execute(
            "INSERT INTO node_fts (id, label, digest) VALUES (?,?,?)",
            (node_id, label, dig),
        )


def add_edge(
    con,
    src: str,
    dst: str,
    rel: str,
    *,
    valid_from: str,
    ingested_at: str | None = None,
) -> None:
    con.execute(
        """
        INSERT OR IGNORE INTO edge
          (src, dst, rel, valid_from, valid_to, ingested_at, invalidated_by)
        VALUES (?,?,?,?,NULL,?,NULL)
        """,
        (src, dst, rel, valid_from, ingested_at or now_iso()),
    )


def invalidate(con, src: str, dst: str, rel: str, *, by: str, as_of: str) -> int:
    """DELETE 금지. valid_to 세팅으로만 무효화. 반환값 = 영향 행 수."""
    cur = con.execute(
        """
        UPDATE edge SET valid_to = ?, invalidated_by = ?
         WHERE src = ? AND dst = ? AND rel = ? AND valid_to IS NULL
        """,
        (as_of, by, src, dst, rel),
    )
    return cur.rowcount


def invalidate_claim(con, claim_id: str, *, by: str, as_of: str) -> int:
    """claim 노드에 연결된 모든 살아있는 엣지를 무효화."""
    cur = con.execute(
        """
        UPDATE edge SET valid_to = ?, invalidated_by = ?
         WHERE (src = ? OR dst = ?) AND valid_to IS NULL
        """,
        (as_of, by, claim_id, claim_id),
    )
    return cur.rowcount


def search(con, query: str, limit: int = 5) -> list[str]:
    """FTS5 + 토큰 OR + LIKE 폴백."""
    tokens = re.findall(r"[\w가-힣]{2,}", query)
    seen: list[str] = []

    def _add(ids: list[str]) -> None:
        for i in ids:
            if i not in seen:
                seen.append(i)

    if tokens:
        q = " OR ".join(tokens)
        try:
            rows = con.execute(
                "SELECT id FROM node_fts WHERE node_fts MATCH ? LIMIT ?", (q, limit)
            ).fetchall()
            _add([r["id"] for r in rows])
        except sqlite3.OperationalError:
            pass

    if len(seen) < limit:
        for tok in tokens[:6]:
            try:
                rows = con.execute(
                    "SELECT id FROM node_fts WHERE node_fts MATCH ? LIMIT ?",
                    (tok, limit),
                ).fetchall()
                _add([r["id"] for r in rows])
            except sqlite3.OperationalError:
                continue
            if len(seen) >= limit:
                break

    if len(seen) < limit:
        for tok in tokens[:4] or [query[:40]]:
            rows = con.execute(
                "SELECT id FROM node WHERE label LIKE ? OR IFNULL(digest,'') LIKE ? LIMIT ?",
                (f"%{tok}%", f"%{tok}%", limit),
            ).fetchall()
            _add([r["id"] for r in rows])
            if len(seen) >= limit:
                break

    return seen[:limit]


def search_operational(con, query: str, limit: int = 5) -> list[str]:
    """운영 질의(재활용·무효화·채널)용 시드. FTS가 비어도 그래프 질의로 시드."""
    q = query.lower()
    ids: list[str] = []

    if any(k in query for k in ("재활용", "다루지 않은", "미언급", "recycle")):
        rows = con.execute(
            """
            SELECT id FROM node
             WHERE kind='concept'
               AND last_seen < date('now', '-90 days')
               AND mention_cnt >= 2
             ORDER BY mention_cnt DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        ids.extend(r["id"] for r in rows)
        # 90일 미언급이 없으면: 최근 14일 미등장 + 언급≥2
        if not ids:
            rows = con.execute(
                """
                SELECT id FROM node
                 WHERE kind='concept'
                   AND last_seen < date('now', '-14 days')
                   AND mention_cnt >= 2
                 ORDER BY last_seen ASC, mention_cnt DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            ids.extend(r["id"] for r in rows)
        if not ids:
            rows = con.execute(
                """
                SELECT id FROM node WHERE kind='concept'
                 ORDER BY mention_cnt ASC, last_seen ASC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            ids.extend(r["id"] for r in rows)

    if any(k in query for k in ("무효화", "stale", "뒤집힌", "인용하고")):
        rows = con.execute(
            """
            SELECT DISTINCT a.id
              FROM node a
              JOIN edge e1 ON e1.src = a.id AND e1.rel IN ('derived_from','cites')
                                          AND e1.valid_to IS NULL
              JOIN node c ON c.id = e1.dst AND c.kind = 'claim'
              JOIN edge e2 ON (e2.src = c.id OR e2.dst = c.id)
                           AND e2.valid_to IS NOT NULL
             WHERE a.kind = 'asset'
             LIMIT ?
            """,
            (limit,),
        ).fetchall()
        ids.extend(r["id"] for r in rows)
        if not ids:
            rows = con.execute(
                """
                SELECT DISTINCT src FROM edge
                 WHERE valid_to IS NOT NULL LIMIT ?
                """,
                (limit,),
            ).fetchall()
            ids.extend(r[0] for r in rows)
        # 무효화 이력이 없으면 claim 노드를 시드로 (수정 큐 공집합도 답변 가능)
        if not ids:
            rows = con.execute(
                """
                SELECT id FROM node WHERE kind='claim'
                 ORDER BY last_seen DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            ids.extend(r["id"] for r in rows)

    if any(k in q for k in ("linkedin", "링크드인", "저장률", "앵글")):
        rows = con.execute(
            """
            SELECT id FROM node
             WHERE kind='asset' AND (id LIKE '%linkedin%' OR label LIKE '%linkedin%')
             ORDER BY last_seen DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        ids.extend(r["id"] for r in rows)
        rows = con.execute(
            """
            SELECT id FROM node WHERE kind='concept'
              AND (label LIKE '%링크%' OR label LIKE '%LinkedIn%' OR label LIKE '%앵글%'
                   OR label LIKE '%저장%' OR label LIKE '%AX%' OR label LIKE '%전환%')
             ORDER BY mention_cnt DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        ids.extend(r["id"] for r in rows)

    if any(k in q for k in ("instagram", "인스타", "캐러셀", "슬라이드")):
        rows = con.execute(
            """
            SELECT id FROM node
             WHERE kind='asset' AND (id LIKE '%instagram%' OR label LIKE '%instagram%')
             ORDER BY last_seen DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        ids.extend(r["id"] for r in rows)
        rows = con.execute(
            """
            SELECT id FROM node WHERE kind='concept'
              AND (label LIKE '%인스타%' OR label LIKE '%캐러셀%' OR label LIKE '%슬라이드%'
                   OR label LIKE '%Instagram%' OR label LIKE '%FAQ%' OR label LIKE '%AX%')
             ORDER BY mention_cnt DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        ids.extend(r["id"] for r in rows)

    if any(k in q for k in ("ctor", "뉴스레터", "open", "click")):
        rows = con.execute(
            """
            SELECT asset_id FROM perf WHERE metric='ctor'
             ORDER BY value DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        ids.extend(r[0] for r in rows)
        if not ids:
            rows = con.execute(
                """
                SELECT id FROM node
                 WHERE kind='asset' AND (id LIKE '%newsletter%' OR label LIKE '%newsletter%')
                 ORDER BY last_seen DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            ids.extend(r["id"] for r in rows)

    out: list[str] = []
    for i in ids:
        if i not in out:
            out.append(i)
    return out[:limit]


def walk(con, seeds: list[str], hops: int = 2, live_only: bool = True) -> list[dict]:
    """재귀 CTE로 N홉 서브그래프. live_only=True 면 무효화된 엣지 제외."""
    if not seeds:
        return []
    placeholders = ",".join("?" * len(seeds))
    live = "AND e.valid_to IS NULL" if live_only else ""
    sql = f"""
        WITH RECURSIVE sub(id, depth) AS (
          SELECT id, 0 FROM node WHERE id IN ({placeholders})
          UNION
          SELECT CASE WHEN e.src = s.id THEN e.dst ELSE e.src END, s.depth + 1
            FROM edge e JOIN sub s
              ON (e.src = s.id OR e.dst = s.id)
           WHERE s.depth < ? {live}
        )
        SELECT n.id, n.kind, n.label, n.digest, n.body_uri,
               n.first_seen, n.last_seen, n.mention_cnt, MIN(s.depth) AS depth
          FROM sub s JOIN node n ON n.id = s.id
         GROUP BY n.id
         ORDER BY depth, n.mention_cnt DESC
    """
    rows = con.execute(sql, (*seeds, hops)).fetchall()
    return [dict(r) for r in rows]


def stats(con) -> dict:
    def one(q: str) -> int:
        return con.execute(q).fetchone()[0]

    return {
        "nodes": one("SELECT COUNT(*) FROM node"),
        "edges_live": one("SELECT COUNT(*) FROM edge WHERE valid_to IS NULL"),
        "edges_invalidated": one("SELECT COUNT(*) FROM edge WHERE valid_to IS NOT NULL"),
        "concepts": one("SELECT COUNT(*) FROM node WHERE kind='concept'"),
        "claims": one("SELECT COUNT(*) FROM node WHERE kind='claim'"),
        "assets": one("SELECT COUNT(*) FROM node WHERE kind='asset'"),
        "perf_rows": one("SELECT COUNT(*) FROM perf"),
    }


def meta_get(con, key: str, default: str | None = None) -> str | None:
    row = con.execute("SELECT val FROM build_meta WHERE key = ?", (key,)).fetchone()
    return row["val"] if row else default


def meta_set(con, key: str, val: str) -> None:
    con.execute(
        "INSERT OR REPLACE INTO build_meta (key, val) VALUES (?, ?)", (key, val)
    )
