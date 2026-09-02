"""Characterization tests for HybridScorer RRF fusion."""
from literature_rag.bm25_retriever import HybridScorer


def test_rrf_overlapping_id_ranks_first():
    scorer = HybridScorer(method="rrf", rrf_k=60)
    bm25 = [("a", 9.0), ("b", 5.0), ("c", 1.0)]
    dense = [("b", 0.1), ("d", 0.2), ("a", 0.3)]  # distances, best first
    fused = scorer.combine_scores(bm25, dense, n_results=4)
    ids = [cid for cid, _ in fused]
    # "a" (rank1+rank3) and "b" (rank2+rank1) appear in both lists -> top two
    assert set(ids[:2]) == {"a", "b"}
    assert len(ids) == 4


def test_rrf_scores_are_rank_based_not_score_based():
    scorer = HybridScorer(method="rrf", rrf_k=60)
    # Same ranks, wildly different raw scores -> identical fused scores
    f1 = scorer.combine_scores([("x", 1000.0)], [("y", 0.0001)], 2)
    f2 = scorer.combine_scores([("x", 0.1)], [("y", 99.0)], 2)
    assert f1 == f2


def test_rrf_empty_bm25_falls_back_to_dense_order():
    scorer = HybridScorer(method="rrf", rrf_k=60)
    dense = [("a", 0.1), ("b", 0.2), ("c", 0.3)]
    fused = scorer.combine_scores([], dense, 3)
    assert [cid for cid, _ in fused] == ["a", "b", "c"]


def test_rrf_respects_n_results():
    scorer = HybridScorer(method="rrf", rrf_k=60)
    bm25 = [(f"b{i}", float(10 - i)) for i in range(10)]
    fused = scorer.combine_scores(bm25, [], 3)
    assert len(fused) == 3
