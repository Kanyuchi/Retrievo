# Phase 1: Hybrid Retrieval in Chat Path + Eval Gate — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire BM25+dense hybrid retrieval into `JobCollectionRAG.query` (the chat/agentic path, currently dense-only) and add a deterministic retrieval-mechanics test gate to CI.

**Architecture:** `JobCollectionRAG` gains an optional injected `BM25Retriever`; when present and `config.retrieval.use_hybrid` is true, dense candidates and BM25 candidates are fused with the existing `HybridScorer` (RRF) by chunk id, fused docs fetched from Chroma by id, then the existing postprocess/graph/rerank steps run unchanged. The router injects the per-job retriever it already maintains. CI gains unit tests for the fusion path using fake embeddings/collections (no API keys needed).

**Tech Stack:** Python 3.12, pytest, ChromaDB (embedded), rank_bm25, FastAPI. All paths relative to `literature_review_rag_api/`.

**Spec:** `ROADMAP.md` → Phase 1 (repo root). Key audit facts: `job_rag.py:217` dense-only query; `routers/jobs.py:121 get_job_bm25_retriever(job_id, collection=None)` returns a ready `BM25Retriever` (builds from Chroma if missing); `bm25_retriever.py:359 HybridScorer(method, dense_weight, rrf_k).combine_scores(bm25_results, dense_results, n_results) -> List[Tuple[chunk_id, score]]`; `BM25Retriever.query(text, n_results) -> List[Tuple[chunk_id, score]]`; upload maintains per-job BM25 (`jobs.py:249`), delete removes (`jobs.py:1508-1510`).

## Global Constraints
- Never regress the existing test suite: `venv/bin? -> use python -m pytest -q tests` must pass after every task.
- No new runtime dependencies.
- Chat API response shape must not change (same dict format from `JobCollectionRAG.query`).
- BM25 candidates can violate `where_filter` (phase/topic/language) — fused results MUST be post-filtered against the metadata conditions before returning.
- Commit after each task: `type: description`, no Co-Authored-By.

---

### Task 1: Characterization tests for HybridScorer (RRF)

**Files:**
- Test (create): `tests/test_hybrid_scorer.py`

**Interfaces:**
- Consumes: `literature_rag.bm25_retriever.HybridScorer` (exists)
- Produces: nothing new — locks in current fusion behavior before we depend on it

- [ ] **Step 1: Write the tests**

```python
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
```

- [ ] **Step 2: Run tests — expect PASS (characterization of existing code)**

Run: `cd literature_review_rag_api && python -m pytest tests/test_hybrid_scorer.py -v`
Expected: 4 passed. If any fail, STOP — the fusion code doesn't behave as documented; report instead of "fixing" the test.

- [ ] **Step 3: Commit**

```bash
git add literature_review_rag_api/tests/test_hybrid_scorer.py
git commit -m "test: characterization tests for HybridScorer RRF fusion"
```

---

### Task 2: Hybrid retrieval in JobCollectionRAG.query

**Files:**
- Modify: `literature_rag/job_rag.py` (constructor ~line 30-48; query ~line 212-222)
- Test (create): `tests/test_job_rag_hybrid.py`

**Interfaces:**
- Consumes: `BM25Retriever.query(text, n_results) -> List[Tuple[str, float]]`, `BM25Retriever.is_ready() -> bool`, `HybridScorer.combine_scores(...)`, `config.retrieval.use_hybrid` / `.bm25_candidates` / `.hybrid_method` / `.dense_weight` / `.rrf_k` (all already in `config/literature_config.yaml` `retrieval:` block — verify with `grep -n "use_hybrid\|bm25_candidates\|rrf_k" config/literature_config.yaml`; if `use_hybrid` is `false`, set it to `true` in this task).
- Produces: `JobCollectionRAG.__init__(..., bm25_retriever: Optional[BM25Retriever] = None)`; private `self._dense_and_hybrid_query(expanded_query, query_embedding, candidate_k, where_filter) -> dict` returning the Chroma-results-shaped dict `{"ids": [[...]], "documents": [[...]], "metadatas": [[...]], "distances": [[...]]}` that the rest of `query()` already consumes.

- [ ] **Step 1: Write failing tests with fake collection + fake retriever**

```python
"""Hybrid fusion inside JobCollectionRAG.query using fakes (no network)."""
from unittest.mock import patch
import pytest


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
    rag.config.retrieval.use_hybrid = True
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_job_rag_hybrid.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'bm25_retriever'`

- [ ] **Step 3: Implement in `job_rag.py`**

3a. Constructor — add parameter and hybrid config (after `self.term_maps = ...` block):

```python
    def __init__(
        self,
        collection: chromadb.Collection,
        embedding_model: str = None,
        term_maps: Optional[Dict[str, List[List[str]]]] = None,
        job_id: Optional[int] = None,
        bm25_retriever: Optional[Any] = None,
    ):
```

```python
        self.bm25_retriever = bm25_retriever
        r = self.config.retrieval
        self._hybrid_config = {
            "enabled": bool(getattr(r, "use_hybrid", False)),
            "bm25_candidates": int(getattr(r, "bm25_candidates", 50)),
            "method": getattr(r, "hybrid_method", "rrf"),
            "dense_weight": float(getattr(r, "dense_weight", 0.7)),
            "rrf_k": int(getattr(r, "rrf_k", 60)),
        }
```

3b. New private method (place above `query`):

```python
    def _hybrid_fuse(self, expanded_query: str, dense_results: dict,
                     candidate_k: int, where_filter) -> dict:
        """Fuse dense Chroma results with BM25 results via RRF; return
        a Chroma-query-shaped dict. Falls back to dense_results on any issue."""
        try:
            if not (self._hybrid_config["enabled"] and self.bm25_retriever
                    and self.bm25_retriever.is_ready()):
                return dense_results

            from .bm25_retriever import HybridScorer

            dense_ids = (dense_results.get("ids") or [[]])[0]
            dense_dist = (dense_results.get("distances") or [[]])[0]
            dense_pairs = list(zip(dense_ids, dense_dist))
            bm25_pairs = self.bm25_retriever.query(
                expanded_query, n_results=self._hybrid_config["bm25_candidates"])

            scorer = HybridScorer(
                method=self._hybrid_config["method"],
                dense_weight=self._hybrid_config["dense_weight"],
                rrf_k=self._hybrid_config["rrf_k"])
            fused = scorer.combine_scores(bm25_pairs, dense_pairs, candidate_k)
            fused_ids = [cid for cid, _ in fused]
            if not fused_ids:
                return dense_results

            fetched = self.collection.get(ids=fused_ids, include=["documents", "metadatas"])
            by_id = {i: (d, m) for i, d, m in zip(
                fetched.get("ids", []), fetched.get("documents", []),
                fetched.get("metadatas", []))}
            dense_dist_map = dict(dense_pairs)

            # Post-filter: BM25 ignores the Chroma where filter
            conditions = []
            if where_filter:
                conditions = where_filter.get("$and", [where_filter])

            def _passes(meta):
                for cond in conditions:
                    for key, val in cond.items():
                        if meta.get(key) != val:
                            return False
                return True

            ids, docs, metas, dists = [], [], [], []
            for cid in fused_ids:
                if cid not in by_id:
                    continue
                doc, meta = by_id[cid]
                if not _passes(meta or {}):
                    continue
                ids.append(cid); docs.append(doc); metas.append(meta)
                dists.append(dense_dist_map.get(cid, 1.0))
            if not ids:
                return dense_results
            return {"ids": [ids], "documents": [docs],
                    "metadatas": [metas], "distances": [dists]}
        except Exception as e:  # never let fusion break retrieval
            logger.warning(f"Hybrid fusion skipped due to error: {e}")
            return dense_results
```

3c. In `query()`, immediately after the first `results = self.collection.query(...)` call (~line 222) and BEFORE the language-fallback block, insert:

```python
        results = self._hybrid_fuse(expanded_query, results, candidate_k, where_filter)
```

(Leave the language-fallback re-query and graph-expansion re-queries dense-only — they are recovery paths; fusing them adds complexity for marginal gain. Note this in the commit message.)

3d. Add `Any` to the `typing` import in `job_rag.py` if not present (it is present: line 10 imports `Any`).

3e. Verify config: `grep -n "use_hybrid" config/literature_config.yaml` — if `use_hybrid: false`, change to `use_hybrid: true`.

- [ ] **Step 4: Run new tests + full suite**

Run: `python -m pytest tests/test_job_rag_hybrid.py tests/test_hybrid_scorer.py -v && python -m pytest -q tests`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add literature_rag/job_rag.py tests/test_job_rag_hybrid.py config/literature_config.yaml
git commit -m "feat: hybrid BM25+dense fusion in JobCollectionRAG chat retrieval path"
```

---

### Task 3: Inject the per-job BM25 retriever at the chat call site

**Files:**
- Modify: `literature_rag/routers/jobs.py:1209` (inside the chat route)
- Test (create): `tests/test_chat_hybrid_injection.py`

**Interfaces:**
- Consumes: `get_job_bm25_retriever(job_id, collection=None)` (jobs.py:121), `JobCollectionRAG(..., bm25_retriever=...)` from Task 2.
- Produces: chat path constructs `JobCollectionRAG` with a live retriever.

- [ ] **Step 1: Write the failing test (source-level wiring check + construction test)**

```python
"""Verify the chat route wires the BM25 retriever into JobCollectionRAG."""
import inspect
import re


def test_chat_route_injects_bm25_retriever():
    from literature_rag.routers import jobs as jobs_router
    src = inspect.getsource(jobs_router)
    # The JobCollectionRAG construction in the chat route must pass bm25_retriever
    pattern = r"JobCollectionRAG\([^)]*bm25_retriever\s*="
    assert re.search(pattern, src), (
        "chat route must construct JobCollectionRAG with bm25_retriever=..."
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_chat_hybrid_injection.py -v`
Expected: FAIL (assertion).

- [ ] **Step 3: Implement — modify jobs.py:1209**

Replace:

```python
        job_rag = JobCollectionRAG(collection, term_maps=term_maps, job_id=job_id)
```

with:

```python
        bm25_for_chat = None
        if config.retrieval.use_hybrid:
            try:
                bm25_for_chat = get_job_bm25_retriever(job_id, collection=collection)
            except Exception as e:
                logger.warning(f"BM25 unavailable for chat on job {job_id}: {e}")
        job_rag = JobCollectionRAG(
            collection, term_maps=term_maps, job_id=job_id,
            bm25_retriever=bm25_for_chat,
        )
```

(`logger` and `config` are already module-level in jobs.py — verify with `grep -n "^logger\|^config" literature_rag/routers/jobs.py`.)

- [ ] **Step 4: Run test + full suite**

Run: `python -m pytest tests/test_chat_hybrid_injection.py -v && python -m pytest -q tests`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add literature_rag/routers/jobs.py tests/test_chat_hybrid_injection.py
git commit -m "feat: inject per-job BM25 retriever into chat retrieval path"
```

---

### Task 4: Deterministic retrieval-mechanics eval gate in CI

**Files:**
- Create: `tests/test_retrieval_mechanics.py`
- Modify: `.github/workflows/ci.yml` only if `pytest -q tests` doesn't already cover new tests (it runs the whole dir — no change expected; verify).

**Interfaces:**
- Consumes: `BM25Retriever`, `BM25Config` (bm25_retriever.py), `HybridScorer`.
- Produces: a CI-gating test that fails if end-to-end BM25→fusion mechanics regress. Uses a tmp-path index, real tokenizer, no network.

- [ ] **Step 1: Write the eval test**

```python
"""Deterministic retrieval-mechanics gate: BM25 index + RRF fusion end to end.

This is NOT a semantic-quality eval (that needs a real corpus + API key —
see scripts/evaluate_retrieval.py). It gates the mechanics: indexing,
persistence, querying, fusion, and top-k behavior.
"""
import pytest
from literature_rag.bm25_retriever import BM25Retriever, BM25Config, HybridScorer

CORPUS = [
    {"chunk_id": "ruhr_1", "text": "Coal mining decline in the Ruhr valley and structural change"},
    {"chunk_id": "ruhr_2", "text": "Green industry formation after coal phase-out in Germany"},
    {"chunk_id": "voc_1", "text": "Varieties of capitalism and institutional coordination"},
    {"chunk_id": "voc_2", "text": "Liberal market economies versus coordinated market economies"},
    {"chunk_id": "misc_1", "text": "Completely unrelated cooking recipe with pasta and tomatoes"},
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
```

**Note on `BM25Config`:** check its actual constructor first — `grep -n "class BM25Config" -A 12 literature_rag/bm25_retriever.py`. If it's a dataclass with different field names (e.g. requires `k1`/`b`), adjust only the constructor call, not the assertions.

- [ ] **Step 2: Run the tests**

Run: `python -m pytest tests/test_retrieval_mechanics.py -v`
Expected: PASS (mechanics already work — this locks them in). If BM25 P@1 fails, investigate the tokenizer before touching thresholds.

- [ ] **Step 3: Confirm CI picks it up**

Run: `grep -n "pytest" ../.github/workflows/ci.yml` (from literature_review_rag_api/) — the workflow must run the whole `tests` dir. If it lists individual files, add the new test files.

- [ ] **Step 4: Commit**

```bash
git add tests/test_retrieval_mechanics.py
git commit -m "test: deterministic retrieval-mechanics gate for CI"
```

---

### Task 5: Deploy and verify on production

**Files:** none (operational)

- [ ] **Step 1: Full local suite green**

Run: `python -m pytest -q tests`
Expected: all pass, no skips in the new files.

- [ ] **Step 2: Push and deploy**

```bash
git push origin main
ssh -i ../.keys/humbowo_ed25519 root@178.105.211.235 \
  "cd /root/Retrievo && git pull -q && cd literature_review_rag_api && docker compose up -d --build api"
```

- [ ] **Step 3: Smoke-verify hybrid on production**

Wait for `https://humbowo.com/api/healthz` → `{"status":"ok"}`, then re-run the E2E flow (register/login/create KB/upload smoke PDF/`GET /api/jobs/{id}/query?question=...`) and confirm results still return. Then check container logs for the hybrid path:

```bash
ssh -i ../.keys/humbowo_ed25519 root@178.105.211.235 \
  "docker logs lit-rag-api 2>&1 | grep -i 'hybrid\|bm25' | tail -5"
```

Expected: no "Hybrid fusion skipped" warnings during the smoke query.

- [ ] **Step 4: Update living docs + commit**

Append session_log entry ("Phase 1 tasks 1-5: hybrid in chat path + CI eval gate"), move roadmap/whats_next items, commit docs, push.

---

## Deferred from Phase 1 (need budget/creds/real corpus — do NOT implement now)
- Cohere reranker integration (needs COHERE_API_KEY from Shaun; existing CrossEncoderReranker stays available but off — too heavy for the 4GB server)
- Chunking A/B (256–512 token experiment) — requires semantic golden set + OpenAI spend; run via `scripts/evaluate_retrieval.py` after corpus re-seeded
- BGE-M3 / AfriE5 multilingual embedding eval — same dependency

## Self-review notes
- Spec coverage: ROADMAP Phase 1 items 1 (hybrid → Tasks 2-3), 2 (eval gate → Task 4; semantic golden set explicitly deferred with reason), 3-5 deferred with reasons above.
- Types checked: `BM25Retriever.query -> List[Tuple[str, float]]` matches HybridScorer input; `combine_scores` returns `List[Tuple[str, float]]`; Chroma `get()` returns flat lists (not nested) — handled in `_hybrid_fuse`.
- The one intentional behavior change: chat retrieval candidates now include BM25 hits. Response schema unchanged.
