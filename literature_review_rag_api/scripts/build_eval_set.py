#!/usr/bin/env python
"""Build a richer eval set from the current corpus metadata."""

from pathlib import Path
from typing import Dict, List, Any, Tuple
import argparse
import yaml

from literature_rag.config import load_config
import chromadb


STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "over", "under", "between",
    "a", "an", "of", "in", "on", "at", "by", "to", "as", "is", "are", "was",
    "were", "this", "that", "these", "those", "study", "studies", "analysis",
    "research", "paper", "evidence", "case", "effects", "impact",
    "aims", "aim", "examining", "investigate", "intends", "develop", "proposes",
    "approach", "method", "methods", "results", "discussion", "conclusion"
}


def extract_keywords(text: str, limit: int = 3) -> List[str]:
    if not text:
        return []
    words = []
    for raw in text.replace("-", " ").replace("/", " ").split():
        word = "".join(ch for ch in raw if ch.isalnum()).lower()
        if not word or word in STOPWORDS or len(word) < 4:
            continue
        if word not in words:
            words.append(word)
        if len(words) >= limit:
            break
    return words


def extract_topic_tokens(topic: str) -> List[str]:
    return [
        "".join(ch for ch in t if ch.isalnum()).lower()
        for t in topic.replace("_", " ").split()
        if t and t.lower() not in STOPWORDS and len(t) > 3
    ]


def load_documents(cfg) -> Dict[str, Dict[str, Any]]:
    client = chromadb.PersistentClient(path=cfg.storage.indices_path)
    collection = client.get_collection(cfg.storage.collection_name)
    data = collection.get(include=["metadatas"])
    docs: Dict[str, Dict[str, Any]] = {}
    for meta in data.get("metadatas", []):
        doc_id = meta.get("doc_id")
        if doc_id and doc_id not in docs:
            docs[doc_id] = meta
    return docs


def build_queries(
    docs: Dict[str, Dict[str, Any]],
    max_groups: int,
    docs_per_query: int,
    include_unfiltered: bool
) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for meta in docs.values():
        topic = meta.get("topic_category") or "Unknown"
        phase = meta.get("phase") or "Unknown"
        groups.setdefault((topic, phase), []).append(meta)

    # Sort groups by size desc for better coverage
    sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)

    queries: List[Dict[str, Any]] = []
    group_count = 0
    for (topic, phase), metas in sorted_groups:
        if group_count >= max_groups:
            break
        metas = sorted(metas, key=lambda m: m.get("doc_id") or "")
        expected = [m.get("doc_id") for m in metas[:docs_per_query] if m.get("doc_id")]
        if not expected:
            continue
        sample_title = metas[0].get("title") or ""
        sample_abstract = metas[0].get("abstract") or ""
        topic_tokens = extract_topic_tokens(topic)
        keywords = extract_keywords(sample_abstract, limit=4)
        if not keywords:
            keywords = extract_keywords(sample_title, limit=3)
        # Prefer keywords that overlap with topic tokens
        filtered = [k for k in keywords if k in topic_tokens]
        keywords = filtered if filtered else keywords
        topic_text = topic.replace("_", " ")
        query = " ".join(topic_tokens[:3]) if topic_tokens else topic_text
        if keywords:
            query = f"{query} " + " ".join(keywords)
        queries.append({
            "id": f"{phase.lower().replace(' ', '_')}_{topic.lower().replace(' ', '_')}",
            "query": query.strip(),
            "expected_doc_ids": expected,
            "n_results": max(5, docs_per_query * 3),
            "phase_filter": phase,
            "topic_filter": topic
        })
        group_count += 1

    if include_unfiltered:
        topic_groups: Dict[str, List[Dict[str, Any]]] = {}
        for meta in docs.values():
            topic = meta.get("topic_category") or "Unknown"
            topic_groups.setdefault(topic, []).append(meta)
        for topic, metas in sorted(topic_groups.items(), key=lambda x: len(x[1]), reverse=True):
            if len(metas) < docs_per_query:
                continue
            metas = sorted(metas, key=lambda m: m.get("doc_id") or "")
            expected = [m.get("doc_id") for m in metas[:docs_per_query] if m.get("doc_id")]
            sample_title = metas[0].get("title") or ""
            sample_abstract = metas[0].get("abstract") or ""
            topic_tokens = extract_topic_tokens(topic)
            keywords = extract_keywords(sample_abstract, limit=4)
            if not keywords:
                keywords = extract_keywords(sample_title, limit=3)
            filtered = [k for k in keywords if k in topic_tokens]
            keywords = filtered if filtered else keywords
            topic_text = topic.replace("_", " ")
            query = " ".join(topic_tokens[:3]) if topic_tokens else topic_text
            if keywords:
                query = f"{query} " + " ".join(keywords)
            queries.append({
                "id": f"unfiltered_{topic.lower().replace(' ', '_')}",
                "query": query.strip(),
                "expected_doc_ids": expected,
                "n_results": max(5, docs_per_query * 3),
            })
            if len(queries) >= max_groups * 2:
                break

    return queries


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a richer eval set from corpus metadata")
    parser.add_argument("--out", default="eval/queries_rich.yaml", help="Output YAML path")
    parser.add_argument("--max-groups", type=int, default=20, help="Max topic/phase groups")
    parser.add_argument("--docs-per-query", type=int, default=3, help="Expected docs per query")
    parser.add_argument("--include-unfiltered", action="store_true", help="Also add unfiltered topic queries")
    args = parser.parse_args()

    cfg = load_config()
    docs = load_documents(cfg)
    queries = build_queries(docs, args.max_groups, args.docs_per_query, args.include_unfiltered)

    output = {"queries": queries}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(output, sort_keys=False, allow_unicode=False))
    print(f"Wrote {len(queries)} queries to {out_path}")


if __name__ == "__main__":
    main()
