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
