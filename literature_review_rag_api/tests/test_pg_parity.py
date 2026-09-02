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
