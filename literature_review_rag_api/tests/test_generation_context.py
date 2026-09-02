"""Repro + regression test: the LLM prompt must contain full chunk content,
not just the truncated citation-header title, for every complexity path
(simple / medium / complex) of AgenticRAGPipeline.

Uses the same Fake* patterns as tests/test_job_rag_hybrid.py (no network).
"""
from unittest.mock import patch

MARKER = "qq7marker9"

# ~300 chars total; marker sits past char 150 so it can never appear in a
# title built from content[:110].
_PREFIX = (
    "Regional economic transition literature discusses many structural "
    "factors influencing post industrial areas across western europe and "
    "several German states over multiple decades since the 1980s, where "
)
CONTENT = _PREFIX + f"the {MARKER} figure was reported as 42000 workers in 2020 by official statistics."
assert len(CONTENT) > 150
assert CONTENT.index(MARKER) > 150

TITLE = CONTENT[:110]


class FakeEmbeddings:
    def embed_query(self, text):
        return [0.1, 0.2, 0.3]


class FakeCollection:
    """Chroma-like collection with a single chunk whose content carries MARKER."""
    name = "job_fake_gen_ctx"
    _store = {
        "c1": (
            CONTENT,
            {
                "doc_id": "d1",
                "phase": "Phase 1",
                "topic_category": "Employment",
                "authors": "Doe",
                "year": 2020,
                "title": TITLE,
            },
        ),
    }

    def count(self):
        return 1

    def query(self, query_embeddings, n_results, where=None, include=None):
        ids = list(self._store.keys())[:n_results] or list(self._store.keys())
        return {
            "ids": [ids],
            "documents": [[self._store[i][0] for i in ids]],
            "metadatas": [[self._store[i][1] for i in ids]],
            "distances": [[0.1 for _ in ids]],
        }

    def get(self, ids, include=None):
        ids = [i for i in ids if i in self._store]
        return {
            "ids": ids,
            "documents": [self._store[i][0] for i in ids],
            "metadatas": [self._store[i][1] for i in ids],
        }


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class FakeCompletions:
    def __init__(self, captured):
        self._captured = captured

    def create(self, messages, **kwargs):
        self._captured.append(messages)
        return _FakeResponse("stub [1]")


class FakeChatNamespace:
    def __init__(self, captured):
        self.completions = FakeCompletions(captured)


class FakeLLMClient:
    """OpenAI-compatible fake client; records every prompt it receives."""

    def __init__(self):
        self.captured_messages = []
        self.chat = FakeChatNamespace(self.captured_messages)

    def all_prompt_text(self) -> str:
        blobs = []
        for messages in self.captured_messages:
            for m in messages:
                blobs.append(m.get("content", ""))
        return "\n".join(blobs)


def make_job_rag():
    from literature_rag.job_rag import JobCollectionRAG

    with patch("literature_rag.job_rag.get_embeddings", return_value=FakeEmbeddings()), \
         patch("literature_rag.job_rag.get_embedding_info",
               return_value={"provider": "fake", "model": "fake"}):
        rag = JobCollectionRAG(FakeCollection(), bm25_retriever=None)
    # Deterministic, network-free behavior (same knobs as test_job_rag_hybrid.py)
    rag._graph_config["enabled"] = False
    rag._reranker_config["enabled"] = False
    rag._hybrid_config["enabled"] = False
    return rag


def make_pipeline():
    from literature_rag.agentic.pipeline import AgenticRAGPipeline

    rag = make_job_rag()
    client = FakeLLMClient()
    pipeline = AgenticRAGPipeline(rag, client, config={})
    return pipeline, client


def test_simple_path_sends_full_chunk_content_to_llm():
    pipeline, client = make_pipeline()

    result = pipeline.run(question="What is the employment figure?", n_sources=3)

    assert result["sources"], "expected at least one cited source"
    assert MARKER in client.all_prompt_text(), (
        "SIMPLE path: full chunk content (with marker past char 150) must reach "
        "the LLM prompt, not just the truncated title"
    )


def test_medium_path_sends_full_chunk_content_to_llm():
    pipeline, client = make_pipeline()

    result = pipeline.run(question="How does deindustrialization affect employment in the region?", n_sources=3)

    assert result["sources"], "expected at least one cited source"
    assert MARKER in client.all_prompt_text(), (
        "MEDIUM path: full chunk content must reach the LLM prompt"
    )


def test_complex_path_sends_full_chunk_content_to_llm():
    pipeline, client = make_pipeline()

    result = pipeline.run(
        question="Compare and contrast the employment effects with the deindustrialization literature "
                  "and synthesize the findings across multiple perspectives over time.",
        n_sources=3,
    )

    assert result["sources"], "expected at least one cited source"
    assert MARKER in client.all_prompt_text(), (
        "COMPLEX path: full chunk content must reach the LLM prompt"
    )


# ---------------------------------------------------------------------------
# The three tests above all pass against the current codebase: _convert_results,
# format_context_for_prompt and the plain (non-hybrid) query path all thread
# full chunk content through correctly for every complexity route.
#
# Extending the repro per the task's fallback instruction ("if it PASSES,
# extend to ... the chat route's chunk plumbing") into JobCollectionRAG's
# hybrid BM25+dense fusion path (job_rag.py) finds the actual bug: when a
# query returns more dense candidates than n_sources, JobCollectionRAG.query()
# does
#   results = self._hybrid_fuse(expanded_query, results, candidate_k, where_filter)
#   results = self._postprocess_results(results, n_results)
# _hybrid_fuse correctly fuses BM25 + dense via RRF and returns fused_ids in
# the correct fused order. But it stamps each surviving chunk's "distance"
# with the RAW DENSE distance (job_rag.py: dists.append(dense_dist_map.get(cid, 1.0))),
# discarding the RRF fusion result. _postprocess_results then re-derives
# "score = 1 - dist" from that raw dense distance and re-sorts/truncates to
# n_results by PURE DENSE SIMILARITY, silently overriding the hybrid fusion
# decision. The chunk that actually answers the question (found and ranked
# by BM25 keyword match) is dropped whenever a topically-similar-but-generic
# chunk beats it on dense distance alone -- exactly the "retrieval found the
# right chunk, but the LLM never saw its content" production symptom.
# ---------------------------------------------------------------------------

GENERIC_CONTENT = (
    "Regional economic transition literature discusses employment effects "
    "broadly across post-industrial areas in western europe."
)
ANSWER_CONTENT = (
    "Section 4 presents detailed labour market results across several industries. "
    f"Specifically the {MARKER} figure was reported as 42000 workers in 2020 "
    "according to official employment statistics for the region."
)


class FakeCollectionTwoChunks:
    """Two candidate chunks: one generic/dense-favored, one BM25-favored
    (the one that actually answers the question)."""
    name = "job_fake_gen_ctx_2"
    _store = {
        "generic": (GENERIC_CONTENT, {
            "doc_id": "d-generic", "phase": "Phase 1",
            "authors": "Doe", "year": 2020, "title": GENERIC_CONTENT[:80],
        }),
        "answer": (ANSWER_CONTENT, {
            "doc_id": "d-answer", "phase": "Phase 1",
            "authors": "Roe", "year": 2021, "title": ANSWER_CONTENT[:80],
        }),
    }

    def count(self):
        return 2

    def query(self, query_embeddings, n_results, where=None, include=None):
        # Dense search ranks the generic chunk first (better cosine match to
        # the literal question wording) and the answer chunk second.
        order = ["generic", "answer"]
        return {
            "ids": [order],
            "documents": [[self._store[i][0] for i in order]],
            "metadatas": [[self._store[i][1] for i in order]],
            "distances": [[0.1, 0.5]],
        }

    def get(self, ids, include=None):
        ids = [i for i in ids if i in self._store]
        return {
            "ids": ids,
            "documents": [self._store[i][0] for i in ids],
            "metadatas": [self._store[i][1] for i in ids],
        }


class FakeBM25AnswerFirst:
    """BM25 strongly prefers the answer chunk (exact keyword match on the
    figure/employment terms)."""

    def is_ready(self):
        return True

    def query(self, text, n_results=50):
        return [("answer", 8.0), ("generic", 1.0)]


def make_hybrid_pipeline():
    from literature_rag.job_rag import JobCollectionRAG
    from literature_rag.agentic.pipeline import AgenticRAGPipeline

    with patch("literature_rag.job_rag.get_embeddings", return_value=FakeEmbeddings()), \
         patch("literature_rag.job_rag.get_embedding_info",
               return_value={"provider": "fake", "model": "fake"}):
        rag = JobCollectionRAG(FakeCollectionTwoChunks(), bm25_retriever=FakeBM25AnswerFirst())
    rag._graph_config["enabled"] = False
    rag._reranker_config["enabled"] = False
    rag._hybrid_config["enabled"] = True

    client = FakeLLMClient()
    pipeline = AgenticRAGPipeline(rag, client, config={})
    return pipeline, client


def test_hybrid_fusion_survives_trim_to_n_sources():
    """The BM25-preferred, answer-bearing chunk must not be silently dropped
    by dense-only re-ranking when the candidate pool is trimmed to n_sources."""
    pipeline, client = make_hybrid_pipeline()

    result = pipeline.run(question="What is the employment figure?", n_sources=1)

    assert result["sources"], "expected at least one cited source"
    assert MARKER in client.all_prompt_text(), (
        "job_rag.py: JobCollectionRAG._postprocess_results re-sorts/truncates "
        "using raw dense distance, discarding the RRF-fused ranking computed "
        "by _hybrid_fuse -- the BM25-surfaced, answer-bearing chunk gets "
        "dropped instead of the generic dense-favored one"
    )
