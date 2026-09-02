"""Verify the chat route wires the BM25 retriever into JobCollectionRAG."""
import inspect
import re


def test_chat_route_injects_bm25_retriever():
    from literature_rag.routers import jobs as jobs_router
    src = inspect.getsource(jobs_router)
    # The JobCollectionRAG construction in the chat route must pass bm25_retriever
    pattern = r"JobCollectionRAG\([^)]*bm25_retriever\s*="
    assert re.search(pattern, src, re.DOTALL), (
        "chat route must construct JobCollectionRAG with bm25_retriever=..."
    )
