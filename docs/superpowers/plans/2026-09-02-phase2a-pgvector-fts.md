# Phase 2a: Vectors + Lexical Search on Supabase Postgres — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Job knowledge bases store vectors + lexical index in Supabase Postgres (pgvector + FTS) behind a `VECTOR_BACKEND` switch, with Chroma as instant rollback — eliminating the embedded-single-writer ChromaDB and pickle-BM25 bottlenecks.

**Architecture:** A `PgVectorStore` class implements the exact Chroma-collection subset the app uses (`add/get/query/delete/count/.name`), plus a `PgClientShim` with `delete_collection`, plus a `PgLexicalRetriever` implementing the `BM25Retriever` query interface (`is_ready()/query(text, n)`) via Postgres FTS — so `JobCollectionRAG._hybrid_fuse` and all routers work unchanged. One table `vector_chunks` holds document text, JSONB metadata, a 1536-dim vector (L2 ops — matches Chroma's default metric), and a generated `tsvector`. `get_job_collection` / `get_job_bm25_retriever` switch on `VECTOR_BACKEND` env (`chroma` default until cutover).

**Tech Stack:** Python 3.12, SQLAlchemy 2 (existing engine), psycopg2, pgvector extension (Supabase built-in), pytest. Local pg tests run against a Docker `pgvector/pgvector:pg17` container, gated on `TEST_PG_URL`.

**Spec:** `ROADMAP.md` → Phase 2 items 1–2. Verified facts: app's Chroma surface is `add/get/query/delete/count` (+ client `delete_collection` at `routers/auth.py:251`, `routers/jobs.py:495,576`); `where` filters are equality-only, optionally under `"$and"`; no `$in`; `get()` returns FLAT lists, `query()` returns NESTED lists; collections were created without `hnsw:space` → L2 distance; embeddings = OpenAI `text-embedding-3-small`, 1536-dim; `get_job_collection` at `routers/jobs.py:100`; `insights.py:29 _get_job_collection` duplicates it; `get_job_bm25_retriever` at `routers/jobs.py:121`.

## Global Constraints
- Full suite green after every task: `./venv/bin/python -m pytest -q tests` (from `literature_review_rag_api/`).
- `VECTOR_BACKEND` defaults to `chroma` — no behavior change until prod cutover (Task 5).
- No new runtime pip dependencies (embeddings passed as `'[1,2,3]'::vector` strings — the `pgvector` python package is NOT needed).
- FTS uses the `'simple'` config (no language stemming — corpus is EN/DE/multilingual).
- All paths relative to `literature_review_rag_api/`.
- Commit per task, `type: description`, no attribution.

---

### Task 1: `pg_store.py` — store, lexical retriever, client shim, schema

**Files:**
- Create: `literature_rag/pg_store.py`
- Test: `tests/test_pg_store.py`

**Interfaces:**
- Consumes: `literature_rag.database.engine` is NOT imported at module level (tests pass their own engine); `sqlalchemy.create_engine`, `sqlalchemy.text`.
- Produces (used by Task 2):
  - `ensure_schema(engine) -> None`
  - `PgVectorStore(name: str, engine)` with `.name`, `.add(ids, embeddings=None, documents=None, metadatas=None)`, `.get(ids=None, where=None, limit=None, include=None) -> dict` (flat lists), `.query(query_embeddings, n_results, where=None, include=None) -> dict` (nested lists), `.delete(ids=None, where=None)`, `.count() -> int`
  - `PgLexicalRetriever(collection_name: str, engine)` with `.is_ready() -> bool`, `.query(text: str, n_results: int = 50) -> List[Tuple[str, float]]`, no-op `.build_index(chunks, save=True)`, `.add_chunks(chunks, save=True) -> int` (returns 0), `.remove_chunks(ids, save=True) -> int` (0), `.remove_by_doc_id(doc_id, save=True) -> int` (0)
  - `PgClientShim(engine)` with `.delete_collection(name)`, `.get_collection(name) -> PgVectorStore`, `.create_collection(name, metadata=None) -> PgVectorStore`

- [ ] **Step 1: Write the failing tests**

```python
"""PgVectorStore / PgLexicalRetriever integration tests.

Requires a Postgres with pgvector. Run one locally with:
  docker run -d --name pgvec-test -e POSTGRES_PASSWORD=test -p 55432:5432 pgvector/pgvector:pg17
  export TEST_PG_URL=postgresql://postgres:test@localhost:55432/postgres
Skipped when TEST_PG_URL is unset (CI provides a service container).
"""
import os
import pytest
from sqlalchemy import create_engine

TEST_PG_URL = os.getenv("TEST_PG_URL")
pytestmark = pytest.mark.skipif(not TEST_PG_URL, reason="TEST_PG_URL not set")


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(TEST_PG_URL, pool_pre_ping=True)
    from literature_rag.pg_store import ensure_schema
    ensure_schema(eng)
    return eng


@pytest.fixture()
def store(engine):
    from literature_rag.pg_store import PgVectorStore, PgClientShim
    PgClientShim(engine).delete_collection("t_col")
    s = PgVectorStore("t_col", engine)
    s.add(
        ids=["c1", "c2", "c3"],
        embeddings=[[1.0] * 1536, [0.5] * 1536, [0.0] * 1536],
        documents=["coal mining in the Ruhr", "varieties of capitalism", "pasta recipe"],
        metadatas=[{"doc_id": "d1", "phase": "Phase 1"},
                   {"doc_id": "d2", "phase": "Phase 2"},
                   {"doc_id": "d3", "phase": "Phase 1"}],
    )
    return s


def test_count_and_name(store):
    assert store.count() == 3
    assert store.name == "t_col"


def test_query_l2_order_and_nested_shape(store):
    out = store.query(query_embeddings=[[1.0] * 1536], n_results=2)
    assert out["ids"][0] == ["c1", "c2"]           # nearest by L2 first
    assert out["documents"][0][0] == "coal mining in the Ruhr"
    assert out["distances"][0][0] < out["distances"][0][1]
    assert out["metadatas"][0][0]["doc_id"] == "d1"


def test_query_where_equality_and_and(store):
    out = store.query(query_embeddings=[[1.0] * 1536], n_results=3,
                      where={"phase": "Phase 1"})
    assert set(out["ids"][0]) == {"c1", "c3"}
    out2 = store.query(query_embeddings=[[1.0] * 1536], n_results=3,
                       where={"$and": [{"phase": "Phase 1"}, {"doc_id": "d3"}]})
    assert out2["ids"][0] == ["c3"]


def test_get_by_ids_flat_shape(store):
    out = store.get(ids=["c2", "c1"], include=["documents", "metadatas"])
    assert set(out["ids"]) == {"c1", "c2"}
    assert len(out["documents"]) == 2 and isinstance(out["documents"][0], str)


def test_get_by_where_and_get_all(store):
    out = store.get(where={"doc_id": "d1"})
    assert out["ids"] == ["c1"]
    assert len(store.get()["ids"]) == 3


def test_get_include_embeddings(store):
    out = store.get(ids=["c1"], include=["embeddings"])
    assert len(out["embeddings"][0]) == 1536


def test_delete_by_ids_and_where(store):
    store.delete(ids=["c3"])
    assert store.count() == 2
    store.delete(where={"doc_id": "d2"})
    assert store.count() == 1


def test_collections_are_isolated(engine, store):
    from literature_rag.pg_store import PgVectorStore
    other = PgVectorStore("t_other", engine)
    assert other.count() == 0


def test_lexical_query_and_ready(engine, store):
    from literature_rag.pg_store import PgLexicalRetriever
    lex = PgLexicalRetriever("t_col", engine)
    assert lex.is_ready()
    hits = lex.query("Ruhr coal mining", n_results=2)
    assert hits and hits[0][0] == "c1" and hits[0][1] > 0
    # OR semantics: any token may match
    assert lex.query("capitalism nonsenseword", 2)[0][0] == "c2"
    # no-op maintenance interface (data lives in the table)
    assert lex.add_chunks([]) == 0 and lex.remove_by_doc_id("d1") == 0


def test_client_shim_delete_collection(engine):
    from literature_rag.pg_store import PgVectorStore, PgClientShim
    s = PgVectorStore("t_del", engine)
    s.add(ids=["x1"], embeddings=[[0.0] * 1536], documents=["temp"], metadatas=[{"doc_id": "dx"}])
    PgClientShim(engine).delete_collection("t_del")
    assert PgVectorStore("t_del", engine).count() == 0
```

- [ ] **Step 2: Start local pgvector container and verify tests fail for the right reason**

```bash
docker run -d --name pgvec-test -e POSTGRES_PASSWORD=test -p 55432:5432 pgvector/pgvector:pg17
export TEST_PG_URL=postgresql://postgres:test@localhost:55432/postgres
./venv/bin/python -m pytest tests/test_pg_store.py -x -q
```
Expected: FAIL `ModuleNotFoundError: literature_rag.pg_store`.

- [ ] **Step 3: Implement `literature_rag/pg_store.py`**

```python
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

from sqlalchemy import text

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
    USING hnsw (embedding vector_l2_ops);
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
        for key, val in cond.items():
            pk, pv = f"wk{i}", f"wv{i}"
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
        embeddings = embeddings or [None] * len(ids)
        documents = documents or [""] * len(ids)
        metadatas = metadatas or [{}] * len(ids)
        with self._engine.begin() as conn:
            for cid, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
                conn.execute(text(
                    "INSERT INTO vector_chunks (chunk_id, collection, document, metadata, embedding) "
                    "VALUES (:id, :c, :doc, CAST(:meta AS jsonb), CAST(:emb AS vector)) "
                    "ON CONFLICT (collection, chunk_id) DO UPDATE SET "
                    "document = EXCLUDED.document, metadata = EXCLUDED.metadata, "
                    "embedding = EXCLUDED.embedding"),
                    {"id": cid, "c": self.name, "doc": doc or "",
                     "meta": json.dumps(meta or {}),
                     "emb": _vec(emb) if emb is not None else None})

    def get(self, ids: Optional[List[str]] = None, where: Optional[dict] = None,
            limit: Optional[int] = None, include: Optional[List[str]] = None) -> dict:
        include = include if include is not None else ["documents", "metadatas"]
        params: Dict[str, Any] = {"c": self.name}
        sql = ("SELECT chunk_id, document, metadata, embedding::text "
               "FROM vector_chunks WHERE collection = :c")
        if ids:
            params["ids"] = tuple(ids)
            sql += " AND chunk_id IN :ids"
        sql += _where_sql(where, params)
        if limit:
            params["lim"] = int(limit)
            sql += " LIMIT :lim"
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
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
        if ids:
            params["ids"] = tuple(ids)
            sql += " AND chunk_id IN :ids"
        sql += _where_sql(where, params)
        if not ids and not where:
            pass  # deleting whole collection is allowed (mirrors chroma delete())
        with self._engine.begin() as conn:
            conn.execute(text(sql), params)


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
```

**Note:** `IN :ids` with tuple params requires `text()` + `bindparam(expanding=True)` in SQLAlchemy 2 — if `chunk_id IN :ids` errors, use:
```python
from sqlalchemy import bindparam
stmt = text(sql).bindparams(bindparam("ids", expanding=True))
```
and pass `params["ids"] = list(ids)`.

- [ ] **Step 4: Run pg tests + full suite**

Run: `TEST_PG_URL=postgresql://postgres:test@localhost:55432/postgres ./venv/bin/python -m pytest tests/test_pg_store.py -v && ./venv/bin/python -m pytest -q tests`
Expected: pg tests pass; full suite still 25+ passed (pg tests skip without the env var).

- [ ] **Step 5: Commit**

```bash
git add literature_rag/pg_store.py tests/test_pg_store.py
git commit -m "feat: Postgres pgvector+FTS store with Chroma-compatible interface"
```

---

### Task 2: `VECTOR_BACKEND` switch in routers

**Files:**
- Modify: `literature_rag/routers/jobs.py` (`get_job_collection` ~line 100, `get_job_bm25_retriever` ~line 121)
- Modify: `literature_rag/routers/insights.py` (`_get_job_collection` ~line 29)
- Modify: `literature_rag/routers/auth.py` (~line 251 delete path)
- Test: `tests/test_backend_switch.py`

**Interfaces:**
- Consumes: `PgVectorStore`, `PgLexicalRetriever`, `PgClientShim`, `ensure_schema` from Task 1; `literature_rag.database.engine`.
- Produces: `vector_backend() -> str` helper in `jobs.py` (reads `VECTOR_BACKEND` env, default `"chroma"`); all three files route through backend-aware getters.

- [ ] **Step 1: Write failing tests**

```python
"""Backend switch: VECTOR_BACKEND=pgvector routes to PgVectorStore paths."""
import importlib
import os
from unittest.mock import patch


def test_default_backend_is_chroma():
    from literature_rag.routers import jobs
    assert jobs.vector_backend() == "chroma"


def test_pgvector_backend_returns_pg_objects():
    from literature_rag.routers import jobs
    from literature_rag.pg_store import PgVectorStore, PgClientShim, PgLexicalRetriever

    class J:  # minimal Job stand-in
        id = 999
        collection_name = "job_test_backend"
        job_name = name = "t"

    with patch.dict(os.environ, {"VECTOR_BACKEND": "pgvector"}):
        with patch.object(jobs, "ensure_pg_schema") as _:
            client, col = jobs.get_job_collection(J())
            assert isinstance(col, PgVectorStore)
            assert isinstance(client, PgClientShim)
            bm25 = jobs.get_job_bm25_retriever(J().id)
            assert isinstance(bm25, PgLexicalRetriever)
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_backend_switch.py -v`
Expected: FAIL (`vector_backend` / `ensure_pg_schema` don't exist).

- [ ] **Step 3: Implement**

3a. In `jobs.py`, add near the top (after existing imports and `config = load_config()`):

```python
from ..pg_store import PgVectorStore, PgLexicalRetriever, PgClientShim, ensure_schema as _pg_ensure_schema

_pg_schema_ready = False


def vector_backend() -> str:
    return os.getenv("VECTOR_BACKEND", "chroma").strip().lower()


def ensure_pg_schema():
    global _pg_schema_ready
    if not _pg_schema_ready:
        from ..database import engine
        _pg_ensure_schema(engine)
        _pg_schema_ready = True
```

(`import os` already exists in jobs.py — verify; add if missing.)

3b. In `get_job_collection` (jobs.py:100), FIRST lines of the function body:

```python
    if vector_backend() == "pgvector":
        from ..database import engine
        ensure_pg_schema()
        return PgClientShim(engine), PgVectorStore(job.collection_name, engine)
```

3c. In `get_job_bm25_retriever` (jobs.py:121), FIRST lines of the function body:

```python
    if vector_backend() == "pgvector":
        from ..database import Job as _Job, get_db_session
        db = get_db_session()
        try:
            job_row = db.query(_Job).filter(_Job.id == job_id).first()
        finally:
            db.close()
        if not job_row:
            return None
        from ..database import engine
        ensure_pg_schema()
        return PgLexicalRetriever(job_row.collection_name, engine)
```

3d. `insights.py:29 _get_job_collection` — replace its body to delegate:

```python
def _get_job_collection(job):
    from .jobs import get_job_collection
    _, collection = get_job_collection(job)
    return collection
```

3e. `auth.py:251` — the account-deletion path builds its own chroma client. Route it the same way: find the block that calls `client.delete_collection(job.collection_name)` and change the client acquisition to:

```python
        from .jobs import get_job_collection
        client, _ = get_job_collection(job)
        client.delete_collection(job.collection_name)
```

(Read the surrounding function first; keep its error handling as-is.)

- [ ] **Step 4: Run new tests + full suite**

Run: `./venv/bin/python -m pytest tests/test_backend_switch.py -v && ./venv/bin/python -m pytest -q tests`
Expected: all pass (default backend unchanged ⇒ zero regressions).

- [ ] **Step 5: Commit**

```bash
git add literature_rag/routers/jobs.py literature_rag/routers/insights.py literature_rag/routers/auth.py tests/test_backend_switch.py
git commit -m "feat: VECTOR_BACKEND switch routing collections to pgvector store"
```

---

### Task 3: Parity gate in CI (pgvector service container)

**Files:**
- Modify: `.github/workflows/ci.yml` (repo root)
- Test: `tests/test_pg_parity.py`

**Interfaces:**
- Consumes: Task 1 classes; `HybridScorer` from `bm25_retriever.py`.
- Produces: CI job runs the full suite WITH `TEST_PG_URL` set, so pg-store + parity tests gate every push.

- [ ] **Step 1: Write the parity test**

```python
"""Parity: hybrid retrieval through PgVectorStore + PgLexicalRetriever
returns the same fused top result as the in-memory reference path."""
import os
import pytest
from sqlalchemy import create_engine

TEST_PG_URL = os.getenv("TEST_PG_URL")
pytestmark = pytest.mark.skipif(not TEST_PG_URL, reason="TEST_PG_URL not set")

DOCS = [
    ("p1", [1.0, 0.0], "coal mining decline in the Ruhr valley"),
    ("p2", [0.0, 1.0], "varieties of capitalism coordination"),
    ("p3", [0.7, 0.7], "green industry after coal phase-out"),
]


def _pad(v):  # 2-dim toy vectors -> 1536
    return v + [0.0] * (1536 - len(v))


@pytest.fixture(scope="module")
def stores():
    from literature_rag.pg_store import (PgVectorStore, PgLexicalRetriever,
                                         PgClientShim, ensure_schema)
    eng = create_engine(TEST_PG_URL, pool_pre_ping=True)
    ensure_schema(eng)
    PgClientShim(eng).delete_collection("parity_col")
    s = PgVectorStore("parity_col", eng)
    s.add(ids=[d[0] for d in DOCS],
          embeddings=[_pad(d[1]) for d in DOCS],
          documents=[d[2] for d in DOCS],
          metadatas=[{"doc_id": d[0]} for d in DOCS])
    return s, PgLexicalRetriever("parity_col", eng)


def test_hybrid_fusion_over_pg_backend(stores):
    from literature_rag.bm25_retriever import HybridScorer
    store, lex = stores
    dense = store.query(query_embeddings=[_pad([1.0, 0.0])], n_results=3)
    dense_pairs = list(zip(dense["ids"][0], dense["distances"][0]))
    lex_pairs = lex.query("Ruhr coal mining", 3)
    fused = HybridScorer(method="rrf").combine_scores(lex_pairs, dense_pairs, 3)
    assert fused[0][0] == "p1"  # lexically AND semantically closest


def test_pg_lexical_matches_expected_ranks(stores):
    _, lex = stores
    assert lex.query("varieties capitalism", 1)[0][0] == "p2"
    assert lex.query("green industry phase-out", 1)[0][0] == "p3"
```

- [ ] **Step 2: Run locally with the container**

Run: `TEST_PG_URL=postgresql://postgres:test@localhost:55432/postgres ./venv/bin/python -m pytest tests/test_pg_parity.py -v`
Expected: PASS.

- [ ] **Step 3: Add pgvector service to CI**

In `.github/workflows/ci.yml`, locate the backend job (the one running `pytest -q tests`) and add under it:

```yaml
    services:
      pgvector:
        image: pgvector/pgvector:pg17
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 55432:5432
        options: >-
          --health-cmd "pg_isready -U postgres" --health-interval 5s
          --health-timeout 5s --health-retries 10
```

and add to that job's test-step `env:`:

```yaml
        env:
          TEST_PG_URL: postgresql://postgres:test@localhost:55432/postgres
```

(Read the existing workflow first and merge minimally — do not restructure other jobs.)

- [ ] **Step 4: Full local suite + push and watch CI**

Run: `TEST_PG_URL=... ./venv/bin/python -m pytest -q tests` → all pass.
Then commit/push and check: `gh run watch --exit-status` (or `gh run list -L1`).

- [ ] **Step 5: Commit**

```bash
git add tests/test_pg_parity.py ../.github/workflows/ci.yml
git commit -m "test: pgvector parity gate with CI service container"
```

---

### Task 4: Chroma → Postgres migration script

**Files:**
- Create: `scripts/migrate_chroma_to_pg.py`

**Interfaces:**
- Consumes: `chromadb.PersistentClient`, `PgVectorStore`, `ensure_schema`, `database.engine`, `database.Job`.
- Produces: idempotent CLI: `python scripts/migrate_chroma_to_pg.py [--indices-path PATH] [--dry-run]`.

- [ ] **Step 1: Write the script**

```python
"""Migrate all job Chroma collections into Postgres vector_chunks.

Idempotent: PgVectorStore.add upserts on (collection, chunk_id).
Usage: python scripts/migrate_chroma_to_pg.py [--indices-path ./indices] [--dry-run]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb  # noqa: E402
from literature_rag.database import engine, get_db_session, Job  # noqa: E402
from literature_rag.pg_store import PgVectorStore, ensure_schema  # noqa: E402

BATCH = 200


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices-path", default="./indices")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ensure_schema(engine)
    client = chromadb.PersistentClient(path=args.indices_path)

    db = get_db_session()
    try:
        jobs = db.query(Job).all()
    finally:
        db.close()

    total = 0
    for job in jobs:
        try:
            col = client.get_collection(job.collection_name)
        except Exception:
            print(f"job {job.id} ({job.collection_name}): no chroma collection, skipping")
            continue
        n = col.count()
        print(f"job {job.id} ({job.collection_name}): {n} chunks")
        if args.dry_run or n == 0:
            continue
        store = PgVectorStore(job.collection_name, engine)
        offset = 0
        while offset < n:
            batch = col.get(include=["documents", "metadatas", "embeddings"],
                            limit=BATCH, offset=offset)
            if not batch["ids"]:
                break
            store.add(ids=batch["ids"],
                      embeddings=[list(e) for e in batch["embeddings"]],
                      documents=batch["documents"],
                      metadatas=batch["metadatas"])
            offset += len(batch["ids"])
            total += len(batch["ids"])
        migrated = store.count()
        status = "OK" if migrated >= n else "MISMATCH"
        print(f"  -> pg rows: {migrated}/{n} {status}")
    print(f"total chunks migrated: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Smoke locally (dry-run against empty local state)**

Run: `./venv/bin/python scripts/migrate_chroma_to_pg.py --dry-run --indices-path /tmp/nonexistent-indices` with `DATABASE_URL=sqlite:///./tmp_mig.db` — expect clean "no collection, skipping"/empty output, exit 0 (sqlite lacks pgvector: run with `--dry-run` only locally; `ensure_schema` must therefore be called AFTER the dry-run check — adjust: move `ensure_schema(engine)` below `if args.dry_run` guard or wrap in try/except with a warning).

- [ ] **Step 3: Commit**

```bash
git add scripts/migrate_chroma_to_pg.py
git commit -m "feat: idempotent Chroma-to-Postgres migration script"
```

---

### Task 5: Production cutover (with rollback lever)

**Files:** none (operational). Server: `root@178.105.211.235`, app dir `/root/Retrievo/literature_review_rag_api`.

- [ ] **Step 1: Deploy code** — push main; on server `git pull && docker compose up -d --build api`; wait for healthz.

- [ ] **Step 2: Migrate data** — run the migration INSIDE the container (has chroma + env):

```bash
ssh <server> "cd /root/Retrievo/literature_review_rag_api && \
  docker compose run --rm -T api python scripts/migrate_chroma_to_pg.py --indices-path /app/indices"
```

Expected: per-job `OK` lines. Verify count independently via psql/psycopg2: `SELECT collection, count(*) FROM vector_chunks GROUP BY 1;`

- [ ] **Step 3: Flip backend** — add `VECTOR_BACKEND=pgvector` to server `.env` AND to `docker-compose.yml` environment passthrough (`- VECTOR_BACKEND=${VECTOR_BACKEND:-chroma}` — commit this line as part of Step 1 if not present); `docker compose up -d api`.

- [ ] **Step 4: E2E verify on production** — login smoke user, create KB, upload the smoke PDF (curl flow from session history), query returns the chunk; then `SELECT count(*) FROM vector_chunks WHERE collection LIKE 'job_%'` grew. Check logs for pg errors: `docker logs lit-rag-api --since 5m | grep -iE 'error|pg_store'`.

- [ ] **Step 5: Rollback lever (document, don't run)** — set `VECTOR_BACKEND=chroma` in server `.env`, `docker compose up -d api`. Chroma data stays on disk untouched until Phase 2b cleanup.

- [ ] **Step 6: Living docs + commit** — session_log entry, whats_next (move item to Done), project_state (architecture line: vectors+FTS in Supabase), push.

---

## Explicitly out of scope (Phase 2b)
Redis ingestion queue, async per-job upload, Redis rate-limiting/OAuth state, uvicorn multi-worker, Chroma data cleanup, legacy default-collection (`literature_rag.py`) migration — the global KB stays on Chroma until deprecated.

## Self-review notes
- Coverage: ROADMAP Phase 2 items 1 (Tasks 1–5) and 2 (PgLexicalRetriever replaces per-job BM25 pickles when backend=pgvector; pickles remain only for the legacy chroma backend). Items 3–5 of Phase 2 → Phase 2b.
- Shim honesty: `get()` flat vs `query()` nested shapes both implemented + tested (the classic chroma trap). `where` grammar limited to equality/$and — matches every call site found (no `$in` anywhere).
- Distance parity: L2 both sides (chroma default ↔ `vector_l2_ops`/`<->`).
- Upload path writes through `collection.add` → shim upsert; BM25 maintenance calls hit PgLexicalRetriever no-ops (tsvector auto-maintained). Delete path: `collection.get(where={"doc_id"}) → delete(ids=...)` works via shim; `remove_by_doc_id` no-op is safe because vector rows are the source of truth for FTS too.
