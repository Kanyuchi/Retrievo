#!/usr/bin/env python
"""Evaluate retrieval precision and citation correctness."""

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List

import yaml

from literature_rag.config import load_config
from literature_rag.literature_rag import LiteratureReviewRAG


def load_queries(path: Path) -> List[Dict[str, Any]]:
    data = yaml.safe_load(path.read_text())
    return data.get("queries", [])


def evaluate_retrieval(rag: LiteratureReviewRAG, queries: List[Dict[str, Any]], default_k: int) -> Dict[str, Any]:
    results = []
    total_hits = 0
    total_expected = 0
    total_precision = 0.0

    for item in queries:
        query = item["query"]
        n_results = item.get("n_results", default_k)
        expected = [d for d in item.get("expected_doc_ids", []) if d and d != "REPLACE_ME"]

        filters = {}
        if item.get("phase_filter"):
            filters["phase_filter"] = item["phase_filter"]
        if item.get("topic_filter"):
            filters["topic_filter"] = item["topic_filter"]

        response = rag.query(question=query, n_results=n_results, **filters)
        retrieved = [m.get("doc_id") for m in response.get("metadatas", [[]])[0]]

        hits = len(set(retrieved) & set(expected)) if expected else 0
        precision = hits / n_results if n_results else 0.0
        recall = hits / len(expected) if expected else None

        if expected:
            total_hits += hits
            total_expected += len(expected)
            total_precision += precision

        results.append({
            "id": item.get("id"),
            "query": query,
            "n_results": n_results,
            "expected_count": len(expected),
            "hits": hits,
            "precision_at_k": round(precision, 4),
            "recall": round(recall, 4) if recall is not None else None,
            "retrieved_doc_ids": retrieved
        })

    expected_queries = [
        q for q in queries
        if [d for d in q.get("expected_doc_ids", []) if d and d != "REPLACE_ME"]
    ]
    summary = {
        "queries": len(queries),
        "avg_precision_at_k": round(total_precision / max(1, len(expected_queries)), 4),
        "overall_recall": round(total_hits / total_expected, 4) if total_expected else None,
    }

    return {"summary": summary, "results": results}


def evaluate_citations(agentic_pipeline, queries: List[Dict[str, Any]], default_k: int) -> Dict[str, Any]:
    citation_results = []

    for item in queries:
        query = item["query"]
        n_results = item.get("n_results", default_k)
        expected = [d for d in item.get("expected_doc_ids", []) if d and d != "REPLACE_ME"]

        filters = {}
        if item.get("phase_filter"):
            filters["phase_filter"] = item["phase_filter"]
        if item.get("topic_filter"):
            filters["topic_filter"] = item["topic_filter"]

        result = agentic_pipeline.run(
            question=query,
            n_sources=n_results,
            phase_filter=filters.get("phase_filter"),
            topic_filter=filters.get("topic_filter")
        )

        cited_doc_ids = [s.get("doc_id") for s in result.get("sources", []) if s.get("doc_id")]
        if expected:
            correct = len(set(cited_doc_ids) & set(expected))
            total = len(cited_doc_ids)
            correctness = correct / total if total else None
        else:
            correct = None
            total = len(cited_doc_ids)
            correctness = None

        citation_results.append({
            "id": item.get("id"),
            "query": query,
            "citations": total,
            "correct_citations": correct,
            "citation_correctness": round(correctness, 4) if correctness is not None else None
        })

    return {"results": citation_results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality")
    parser.add_argument("--queries", default="eval/queries.yaml", help="Path to queries YAML")
    parser.add_argument("--out", default=None, help="Optional JSON output path")
    parser.add_argument("--chat", action="store_true", help="Evaluate citation correctness using agentic pipeline (requires GROQ_API_KEY)")
    parser.add_argument("--no-rerank", action="store_true", help="Disable reranking for this run")
    args = parser.parse_args()

    cfg = load_config()
    rag_config = {
        "device": cfg.embedding.device,
        "collection_name": cfg.storage.collection_name,
        "expand_queries": cfg.retrieval.expand_queries,
        "max_expansions": cfg.retrieval.max_expansions,
        "use_reranking": cfg.retrieval.use_reranking,
        "reranker_model": cfg.retrieval.reranker_model,
        "rerank_top_k": cfg.retrieval.rerank_top_k,
        "normalization_enable": cfg.normalization.enable,
        "term_maps": cfg.normalization.term_maps
    }
    if args.no_rerank:
        rag_config["use_reranking"] = False

    rag = LiteratureReviewRAG(
        chroma_path=cfg.storage.indices_path,
        config=rag_config,
        embedding_model=cfg.embedding.model
    )

    queries = load_queries(Path(args.queries))
    retrieval_report = evaluate_retrieval(rag, queries, cfg.retrieval.default_n_results)

    report: Dict[str, Any] = {"retrieval": retrieval_report}

    if args.chat and cfg.agentic.enabled and cfg.llm.groq_api_key:
        from groq import Groq
        from literature_rag.agentic import AgenticRAGPipeline

        groq_client = Groq(api_key=cfg.llm.groq_api_key)
        agentic_config = {
            "classification": {
                "simple_max_words": cfg.agentic.classification.simple_max_words,
                "complex_min_topics": cfg.agentic.classification.complex_min_topics,
                "complex_min_words": cfg.agentic.classification.complex_min_words,
            },
            "thresholds": {
                "evaluation_sufficient": cfg.agentic.thresholds.evaluation_sufficient,
                "citation_accuracy_min": cfg.agentic.thresholds.citation_accuracy_min,
                "max_retrieval_retries": cfg.agentic.thresholds.max_retrieval_retries,
                "max_regeneration_retries": cfg.agentic.thresholds.max_regeneration_retries,
            },
            "agents": cfg.agentic.agents,
        }

        pipeline = AgenticRAGPipeline(rag, groq_client, agentic_config)
        citation_report = evaluate_citations(pipeline, queries, cfg.retrieval.default_n_results)
        report["citations"] = citation_report

    output = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
