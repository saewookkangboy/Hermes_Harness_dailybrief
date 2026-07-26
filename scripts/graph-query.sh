#!/usr/bin/env bash
# 그래프 운영 질의. 즉시 실무 가치가 나오는 3종.
set -euo pipefail
STUDIO="${HERMES_STUDIO:-${HERMES_WORKDIR:-$HOME/hermes-content-studio}}"
DB="$STUDIO/content/wiki/graph.db"
cd "$STUDIO"

[[ -f "$DB" ]] || { echo "graph.db 없음. ./scripts/wiki-graph.sh --force --rebuild 먼저 실행" >&2; exit 1; }

usage() {
  cat <<'EOF'
usage: graph-query.sh <query> [options]

  stale-citations      무효화된 claim을 인용한 채 살아있는 발행물 → 수정 큐
  top-concepts         CTOR 상위 성과 에셋이 공통으로 쓴 concept → 앵글 힌트
  recycle-candidates   90일 이상 미언급 concept → 재활용 후보
  stats                그래프 통계
EOF
}

Q="${1:-}"; shift || true

case "$Q" in
  stale-citations)
    sqlite3 -header -column "$DB" <<'SQL'
SELECT a.id            AS asset,
       a.body_uri      AS path,
       c.label         AS stale_claim,
       e2.invalidated_by AS invalidated_by,
       e2.valid_to     AS invalid_since
  FROM node a
  JOIN edge e1 ON e1.src = a.id AND e1.rel IN ('derived_from','cites')
                              AND e1.valid_to IS NULL
  JOIN node c  ON c.id = e1.dst AND c.kind = 'claim'
  JOIN edge e2 ON (e2.src = c.id OR e2.dst = c.id) AND e2.valid_to IS NOT NULL
 WHERE a.kind = 'asset'
 GROUP BY a.id, c.id
 ORDER BY e2.valid_to DESC
 LIMIT 30;
SQL
    ;;

  top-concepts)
    sqlite3 -header -column "$DB" <<'SQL'
SELECT n.label                  AS concept,
       COUNT(DISTINCT p.asset_id) AS assets,
       ROUND(AVG(p.value), 4)   AS avg_ctor,
       MAX(n.last_seen)         AS last_used
  FROM perf p
  JOIN edge e ON e.src = p.asset_id AND e.rel = 'derived_from' AND e.valid_to IS NULL
  JOIN node n ON n.id = e.dst AND n.kind = 'concept'
 WHERE p.metric = 'ctor'
 GROUP BY n.id
HAVING assets >= 2
 ORDER BY avg_ctor DESC
 LIMIT 20;
SQL
    ;;

  recycle-candidates)
    sqlite3 -header -column "$DB" <<'SQL'
SELECT id, label, last_seen, mention_cnt
  FROM node
 WHERE kind = 'concept'
   AND last_seen < date('now', '-90 days')
   AND mention_cnt >= 2
 ORDER BY mention_cnt DESC, last_seen ASC
 LIMIT 25;
SQL
    ;;

  stats)
    cat "$STUDIO/content/wiki/graph-stats.json" 2>/dev/null || \
      PYTHONPATH=scripts python3 -c "
import sys,json; sys.path.insert(0,'scripts')
from lib import graph as G
con=G.connect(); print(json.dumps(G.stats(con), indent=2, ensure_ascii=False))"
    ;;

  *) usage; exit 2 ;;
esac
