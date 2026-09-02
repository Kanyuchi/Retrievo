"""Hybrid fusion inside JobCollectionRAG.query using fakes (no network)."""
from unittest.mock import patch


class FakeEmbeddings:
    def embed_query(self, text):
        return [0.1, 0.2, 0.3]


class FakeCollection:
    """Chroma-like: 4 chunks, dense order c1,c2,c3; c4 only findable via BM25."""
    name = "job_fake"
    _store = {
        "c1": ("alpha beta", {"doc_id": "d1", "phase": "Phase 1"}),
        "c2": ("gamma delta", {"doc_id": "d2", "phase": "Phase 1"}),
        "c3": ("epsilon zeta", {"doc_id": "d3", "phase": "Phase 2"}),
        "c4": ("needle text", {"doc_id": "d4", "phase": "Phase 1"}),
    }

    def count(self):
        return 4

    def query(self, query_embeddings, n_results, where=None, include=None):
        order = ["c1", "c2", "c3"][:n_results]
        return {
            "ids": [order],
            "documents": [[self._store[i][0] for i in order]],
            "metadatas": [[self._store[i][1] for i in order]],
            "distances": [[0.1 * (k + 1) for k in range(len(order))]],
        }

    def get(self, ids, include=None):
        ids = [i for i in ids if i in self._store]
        return {
            "ids": ids,
            "documents": [self._store[i][0] for i in ids],
            "metadatas": [self._store[i][1] for i in ids],
        }


class FakeBM25:
    def is_ready(self):
        return True

    def query(self, text, n_results=50):
        return [("c4", 7.0), ("c2", 3.0)]  # c4 is BM25-only


def make_rag(bm25):
    from literature_rag.job_rag import JobCollectionRAG
    with patch("literature_rag.job_rag.get_embeddings", return_value=FakeEmbeddings()), \
         patch("literature_rag.job_rag.get_embedding_info",
               return_value={"provider": "fake", "model": "fake"}):
        rag = JobCollectionRAG(FakeCollection(), bm25_retriever=bm25)
    # force deterministic behavior for the test
    rag._graph_config["enabled"] = False
    rag._reranker_config["enabled"] = False
    rag._hybrid_config["enabled"] = True
    return rag


def test_hybrid_surfaces_bm25_only_chunk():
    rag = make_rag(FakeBM25())
    out = rag.query("needle", n_results=4)
    docs = out["documents"][0]
    assert any("needle" in d for d in docs), "BM25-only chunk must appear in fused results"


def test_no_bm25_retriever_falls_back_to_dense():
    rag = make_rag(None)
    out = rag.query("needle", n_results=3)
    assert not any("needle" in d for d in out["documents"][0])


def test_hybrid_respects_where_filter_postfilter():
    rag = make_rag(FakeBM25())
    out = rag.query("needle", n_results=4, phase_filter="Phase 1")
    for meta in out["metadatas"][0]:
        assert meta.get("phase") == "Phase 1"
