"""Deterministic retrieval-mechanics gate: BM25 index + RRF fusion end to end.

This is NOT a semantic-quality eval (that needs a real corpus + API key —
see scripts/evaluate_retrieval.py). It gates the mechanics: indexing,
persistence, querying, fusion, and top-k behavior.
"""
import pytest

from literature_rag.bm25_retriever import BM25Retriever, BM25Config, HybridScorer

CORPUS = [
    {"text": "Coal mining decline in the Ruhr valley and structural change",
     "metadata": {"chunk_id": "ruhr_1"}},
    {"text": "Green industry formation after coal phase-out in Germany",
     "metadata": {"chunk_id": "ruhr_2"}},
    {"text": "Varieties of capitalism and institutional coordination",
     "metadata": {"chunk_id": "voc_1"}},
    {"text": "Liberal market economies versus coordinated market economies",
     "metadata": {"chunk_id": "voc_2"}},
    {"text": "Completely unrelated cooking recipe with pasta and tomatoes",
     "metadata": {"chunk_id": "misc_1"}},
]

GOLDEN = [
    ("coal mining Ruhr structural change", {"ruhr_1"}),
    ("green industry coal phase-out", {"ruhr_2"}),
    ("varieties of capitalism coordination", {"voc_1"}),
    ("coordinated market economies", {"voc_2"}),
]


@pytest.fixture()
def bm25(tmp_path):
    r = BM25Retriever(BM25Config(index_path=str(tmp_path / "bm25_test.pkl")))
    r.build_index(CORPUS, save=True)
    return r


def test_bm25_golden_precision_at_1(bm25):
    hits = 0
    for query, expected in GOLDEN:
        top = bm25.query(query, n_results=1)
        if top and top[0][0] in expected:
            hits += 1
    assert hits == len(GOLDEN), f"BM25 P@1 regressed: {hits}/{len(GOLDEN)}"


def test_bm25_index_roundtrip(bm25, tmp_path):
    fresh = BM25Retriever(BM25Config(index_path=str(tmp_path / "bm25_test.pkl")))
    assert fresh.load_index() and fresh.is_ready()
    assert fresh.query("Ruhr coal", 1)[0][0] == "ruhr_1"


def test_fusion_beats_single_method_on_split_corpus(bm25):
    # dense retriever "knows" voc docs; bm25 knows everything lexical
    dense = [("voc_1", 0.1), ("voc_2", 0.2)]
    bm25_res = bm25.query("Ruhr coal mining", 5)
    fused = HybridScorer(method="rrf").combine_scores(bm25_res, dense, 4)
    fused_ids = {cid for cid, _ in fused}
    assert "ruhr_1" in fused_ids and "voc_1" in fused_ids
