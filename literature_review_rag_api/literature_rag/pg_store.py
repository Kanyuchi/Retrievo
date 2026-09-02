"""Postgres-backed vector + lexical store (pgvector + FTS).

Implements the exact chromadb.Collection subset the app uses, so it is a
drop-in behind get_job_collection(). Embeddings are sent as '[..]'::vector
string literals (no pgvector python package needed). Distance = L2 (<->),
matching Chroma's default metric. FTS uses the 'simple' config (multilingual
corpus: EN/DE/African languages — no stemming assumptions).
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import bindparam, text

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536

_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS vector_chunks (
    chunk_id   TEXT NOT NULL,
    collection TEXT NOT NULL,
    document   TEXT NOT NULL DEFAULT '',
    metadata   JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding  vector(1536),
    tsv        tsvector GENERATED ALWAYS AS (to_tsvector('simple', document)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (collection, chunk_id)
);
CREATE INDEX IF NOT EXISTS idx_vc_collection ON vector_chunks (collection);
CREATE INDEX IF NOT EXISTS idx_vc_docid ON vector_chunks (collection, (metadata->>'doc_id'));
CREATE INDEX IF NOT EXISTS idx_vc_tsv ON vector_chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS idx_vc_embedding ON vector_chunks
    USING hnsw (embedding vector_l2_ops)
"""


def ensure_schema(engine) -> None:
    """Create extension, table, and indexes (idempotent)."""
    with engine.begin() as conn:
        for stmt in _SCHEMA.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
    logger.info("pg_store schema ensured")


def _vec(embedding: List[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def _where_sql(where: Optional[dict], params: dict) -> str:
    """Translate the app's equality/$and where grammar to SQL."""
    if not where:
        return ""
    conditions = where.get("$and", [where])
    parts = []
    for i, cond in enumerate(conditions):
        for j, (key, val) in enumerate(cond.items()):
            pk, pv = f"wk{i}_{j}", f"wv{i}_{j}"
            params[pk], params[pv] = key, str(val)
            parts.append(f"metadata->>:{pk} = :{pv}")
    return (" AND " + " AND ".join(parts)) if parts else ""


class PgVectorStore:
    """chromadb.Collection-compatible subset backed by Postgres."""

    def __init__(self, name: str, engine):
        self.name = name
        self._engine = engine

    def count(self) -> int:
        with self._engine.connect() as conn:
            return conn.execute(
                text("SELECT count(*) FROM vector_chunks WHERE collection = :c"),
                {"c": self.name}).scalar() or 0

    def add(self, ids: List[str], embeddings: Optional[List[List[float]]] = None,
            documents: Optional[List[str]] = None,
            metadatas: Optional[List[dict]] = None) -> None:
        embeddings = embeddings if embeddings is not None else [None] * len(ids)
        documents = documents if documents is not None else [""] * len(ids)
        metadatas = metadatas if metadatas is not None else [{}] * len(ids)
        stmt = text(
            "INSERT INTO vector_chunks (chunk_id, collection, document, metadata, embedding) "
            "VALUES (:id, :c, :doc, CAST(:meta AS jsonb), CAST(:emb AS vector)) "
            "ON CONFLICT (collection, chunk_id) DO UPDATE SET "
            "document = EXCLUDED.document, metadata = EXCLUDED.metadata, "
            "embedding = EXCLUDED.embedding")
        with self._engine.begin() as conn:
            for cid, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
                conn.execute(stmt, {
                    "id": cid, "c": self.name, "doc": doc or "",
                    "meta": json.dumps(meta or {}),
                    "emb": _vec(emb) if emb is not None else None})

    def get(self, ids: Optional[List[str]] = None, where: Optional[dict] = None,
            limit: Optional[int] = None, offset: Optional[int] = None,
            include: Optional[List[str]] = None) -> dict:
        include = include if include is not None else ["documents", "metadatas"]
        params: Dict[str, Any] = {"c": self.name}
        sql = ("SELECT chunk_id, document, metadata, embedding::text "
               "FROM vector_chunks WHERE collection = :c")
        binds = []
        if ids:
            params["ids"] = list(ids)
            sql += " AND chunk_id IN :ids"
            binds.append(bindparam("ids", expanding=True))
        sql += _where_sql(where, params)
        sql += " ORDER BY created_at, chunk_id"
        if limit:
            params["lim"] = int(limit)
            sql += " LIMIT :lim"
        if offset:
            params["off"] = int(offset)
            sql += " OFFSET :off"
        stmt = text(sql)
        if binds:
            stmt = stmt.bindparams(*binds)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt, params).fetchall()
        out: Dict[str, Any] = {"ids": [r[0] for r in rows]}
        if "documents" in include:
            out["documents"] = [r[1] for r in rows]
        if "metadatas" in include:
            out["metadatas"] = [r[2] for r in rows]
        if "embeddings" in include:
            out["embeddings"] = [json.loads(r[3]) if r[3] else None for r in rows]
        return out

    def query(self, query_embeddings: List[List[float]], n_results: int = 10,
              where: Optional[dict] = None, include: Optional[List[str]] = None) -> dict:
        params: Dict[str, Any] = {"c": self.name, "q": _vec(query_embeddings[0]),
                                  "n": int(n_results)}
        sql = ("SELECT chunk_id, document, metadata, embedding <-> CAST(:q AS vector) AS dist "
               "FROM vector_chunks WHERE collection = :c AND embedding IS NOT NULL")
        sql += _where_sql(where, params)
        sql += " ORDER BY dist ASC LIMIT :n"
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
        return {"ids": [[r[0] for r in rows]],
                "documents": [[r[1] for r in rows]],
                "metadatas": [[r[2] for r in rows]],
                "distances": [[float(r[3]) for r in rows]]}

    def delete(self, ids: Optional[List[str]] = None, where: Optional[dict] = None) -> None:
        params: Dict[str, Any] = {"c": self.name}
        sql = "DELETE FROM vector_chunks WHERE collection = :c"
        binds = []
        if ids:
            params["ids"] = list(ids)
            sql += " AND chunk_id IN :ids"
            binds.append(bindparam("ids", expanding=True))
        sql += _where_sql(where, params)
        stmt = text(sql)
        if binds:
            stmt = stmt.bindparams(*binds)
        with self._engine.begin() as conn:
            conn.execute(stmt, params)


class PgLexicalRetriever:
    """BM25Retriever-compatible lexical search on Postgres FTS.

    Index maintenance methods are no-ops: the tsvector column is generated
    from the same rows PgVectorStore writes — nothing separate to maintain.
    """

    def __init__(self, collection_name: str, engine):
        self.collection_name = collection_name
        self._engine = engine

    def is_ready(self) -> bool:
        with self._engine.connect() as conn:
            return bool(conn.execute(
                text("SELECT 1 FROM vector_chunks WHERE collection = :c LIMIT 1"),
                {"c": self.collection_name}).scalar())

    def query(self, query_text: str, n_results: int = 50) -> List[Tuple[str, float]]:
        tokens = [t for t in "".join(
            ch if ch.isalnum() else " " for ch in query_text).split() if len(t) > 1]
        if not tokens:
            return []
        tsquery = " | ".join(tokens)  # OR semantics, like BM25 recall
        with self._engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT chunk_id, ts_rank(tsv, to_tsquery('simple', :q)) AS rank "
                "FROM vector_chunks WHERE collection = :c "
                "AND tsv @@ to_tsquery('simple', :q) "
                "ORDER BY rank DESC LIMIT :n"),
                {"q": tsquery, "c": self.collection_name, "n": int(n_results)}).fetchall()
        return [(r[0], float(r[1])) for r in rows]

    # ---- no-op maintenance interface (parity with BM25Retriever) ----
    def build_index(self, chunks, save: bool = True) -> None:
        return None

    def add_chunks(self, chunks, save: bool = True) -> int:
        return 0

    def remove_chunks(self, chunk_ids, save: bool = True) -> int:
        return 0

    def remove_by_doc_id(self, doc_id: str, save: bool = True) -> int:
        return 0


class PgClientShim:
    """Client-like object: the app only calls delete_collection / (get|create)_collection."""

    def __init__(self, engine):
        self._engine = engine

    def delete_collection(self, name: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM vector_chunks WHERE collection = :c"), {"c": name})

    def get_collection(self, name: str) -> PgVectorStore:
        return PgVectorStore(name, self._engine)

    def create_collection(self, name: str, metadata: Optional[dict] = None) -> PgVectorStore:
        return PgVectorStore(name, self._engine)
