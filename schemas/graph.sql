-- Hermes Content Studio — 누적 개념 그래프 (bi-temporal)
-- 원칙: 본문은 DB에 넣지 않는다. body_uri 참조 + digest(200자)만.
-- 원칙: DELETE 금지. 무효화는 edge.valid_to 세팅으로만.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS node (
  id          TEXT PRIMARY KEY,
  kind        TEXT NOT NULL
                CHECK (kind IN ('concept','claim','source','asset','angle')),
  label       TEXT NOT NULL,
  body_uri    TEXT,
  digest      TEXT,
  first_seen  TEXT NOT NULL,
  last_seen   TEXT NOT NULL,
  mention_cnt INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS edge (
  src            TEXT NOT NULL REFERENCES node(id),
  dst            TEXT NOT NULL REFERENCES node(id),
  rel            TEXT NOT NULL
                   CHECK (rel IN ('cites','derived_from','contradicts',
                                  'published_to','mentions','scored')),
  valid_from     TEXT NOT NULL,
  valid_to       TEXT,
  ingested_at    TEXT NOT NULL,
  invalidated_by TEXT,
  PRIMARY KEY (src, dst, rel, valid_from)
);

CREATE TABLE IF NOT EXISTS perf (
  asset_id TEXT NOT NULL REFERENCES node(id),
  metric   TEXT NOT NULL,
  value    REAL NOT NULL,
  period   TEXT NOT NULL,
  source   TEXT NOT NULL DEFAULT 'ctor-ledger',
  PRIMARY KEY (asset_id, metric, period)
);

CREATE VIRTUAL TABLE IF NOT EXISTS node_fts
  USING fts5(id UNINDEXED, label, digest, tokenize='unicode61');

CREATE INDEX IF NOT EXISTS idx_edge_live  ON edge(rel, dst) WHERE valid_to IS NULL;
CREATE INDEX IF NOT EXISTS idx_edge_src   ON edge(src);
CREATE INDEX IF NOT EXISTS idx_node_kind  ON node(kind, last_seen);

CREATE TABLE IF NOT EXISTS build_meta (
  key TEXT PRIMARY KEY,
  val TEXT NOT NULL
);
