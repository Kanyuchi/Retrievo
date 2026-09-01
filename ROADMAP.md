# Humbowo — Product & Engineering Roadmap

_Synthesized 2026-09-02 from three research passes: codebase architecture audit, state-of-the-art RAG survey, and market/monetization research. Full reports in session history; key sources cited inline._

## Strategy in one paragraph

Humbowo's wedge is the underserved middle: **multi-tenant workspaces + trustworthy citations + a knowledge graph, self-serve, EU-hosted** — above ChatPDF/Humata/NotebookLM (single-tenant, no B2B trust posture) and far below Glean (~$45–75/seat, ~$99k ACV, enterprise-only). Land academic/research users as top-of-funnel (they validate quality, pay $10–25/mo), convert **consulting/agency teams and NGO/development orgs** on Team seats ($15–30/seat, 3-seat minimum). Germany/EU sales run on compliance (DPA, EU residency — which we already have: Falkenstein + Frankfurt); African sales run on product pragmatics (mobile money, offline tolerance). Defer Mittelstand/enterprise 6–12 months.

**Engineering doctrine:** ~73% of RAG failures are retrieval failures, not generation. Budget goes to retrieval quality and its measurement before any new surface area. Every phase ships with tests + a retrieval-eval gate in CI; nothing merges that regresses the golden set.

---

## Phase 0 — Launch hygiene (days)
Goal: the deployed product is safe, observable, and fully functional.

1. Working Groq key (`gsk_…`) or switch chat provider → chat live
2. Object storage: R2 or Hetzner Object Storage bucket; **add `endpoint_url` support to `storage.py`** (boto3 client currently can't target non-AWS S3)
3. Full browser smoke test: register → create KB → upload → search → chat → export
4. `REQUIRE_HTTPS=true`; Hetzner Cloud firewall (22/80/443); server backups (Hetzner auto-backup); uptime monitor on `/api/healthz`
5. Fix per-job upload route (`routers/jobs.py:1278`) blocking sync — minimum: move to BackgroundTasks like the global path

**Test gate:** existing pytest suite green; manual E2E checklist recorded in session_log.

## Phase 1 — Retrieval quality + eval harness (1–2 weeks)
Goal: retrieval is provably good and cannot silently regress. This is the highest-leverage phase in the whole plan.

1. **Wire hybrid retrieval into the production path.** Audit finding: `JobCollectionRAG.query` is dense-only; BM25/RRF code exists (`bm25_retriever.py`, `hybrid` config) but is only called in the legacy global path. Hybrid is table stakes (+~17% recall).
2. **Golden set + eval in CI:** 50–100 real queries; RAGAS-style faithfulness + context precision/recall (repo already has `scripts/evaluate_retrieval.py` + `eval/queries.yaml` — wire into CI as a deploy gate).
3. **Reranker:** enable the existing `CrossEncoderReranker` OR (recommended, 4GB-RAM server) use Cohere Rerank API; measure on the golden set before/after.
4. **Chunking review:** research consensus favors 256–512 tokens, 10–20% overlap; current config is char-based 1024/2048 hierarchical — A/B on the golden set before changing defaults.
5. Multilingual check: current embeddings are OpenAI-only; evaluate BGE-M3 (100+ languages incl. German; African-language options: AfriE5) on a German + target-language query set. Decide with data, not vibes — embedding switch forces full re-index.

**Test gate:** golden-set metrics recorded pre/post each change; CI fails on regression.

## Phase 2 — Scale-ready architecture (2–3 weeks)
Goal: two app replicas could serve traffic; ingestion survives crashes. Fixes the audit's bottleneck list.

1. **ChromaDB → Supabase pgvector.** Kills the embedded-single-writer bottleneck, unifies vectors + metadata + SQL filters (user/job/phase/year) in the Postgres we already run. Consensus: pgvector is right below ~50M vectors.
2. **BM25 pickles → Postgres full-text search** (`tsvector` + `ts_rank`), hybrid via RRF in SQL — one query, no pickle rebuilds, no file locking, incremental updates for free.
3. **Ingestion queue:** Redis + worker container (repo's `worker.py` abstraction exists but is barely used); `acks_late` semantics so crashed workers don't drop documents; per-job upload becomes enqueue + progress polling (UploadTaskRecord already models this).
4. Redis-backed rate limiting + OAuth state (both currently in-memory, single-instance only); uvicorn multi-worker.
5. Modular pipeline interfaces (chunker/embedder/retriever/reranker independently swappable) — the 2026 "modular RAG" doctrine, and what makes future model swaps cheap.

**Test gate:** integration tests for pgvector + FTS retrieval parity vs. golden set; kill-a-worker-mid-ingest test; 2-replica docker-compose smoke.

## Phase 3 — Monetization (2–3 weeks, can overlap Phase 2)
Goal: someone can pay us.

1. **Wire the existing quota scaffolding** (`quotas.py` PlanTier/QuotaService — built but not enforced on routes) into upload/KB-creation/query routes; make rate limits tier-aware.
2. **Pricing:** Free (1 workspace, ~3 docs, capped queries — enough to feel citation quality) / Pro €19/mo / Team €25/seat/mo, 3-seat min / Academic-NGO 40–50% off with .edu/.org verification. Upgrade triggers = document + seat count, never query caps (reads punitive).
3. **Stripe** subscription + customer portal + webhook → `plan_tier`; billing page in webapp.
4. **Team workspaces:** shared KBs with roles (owner/editor/viewer) — jobs are single-owner today; this is THE feature separating us from every cheap competitor and it's what Team pricing sells. (Settings/Team.tsx page already stubbed.)
5. **Paystack or Flutterwave** alongside Stripe for African checkout (mobile money) — small effort, removes the biggest African payment blocker.

**Test gate:** quota enforcement tests per tier; Stripe webhook tests (test mode); E2E upgrade/downgrade flow.

## Phase 4 — EU trust package (1 week, mostly non-code)
1. DPA (Art. 28) template + published sub-processor list (Hetzner, Supabase, OpenAI, Groq/LLM provider, Stripe) — a hard procurement gate in Germany; BfDI fined Vodafone €15M over a deficient DPA in 2025
2. Privacy policy + Impressum (German law), data deletion (account + KB purge endpoints — verify cascade deletes truly remove vectors/S3 objects)
3. "Your data stays in the EU" page: Falkenstein server + Frankfurt DB is a real differentiator vs. US-hosted competitors — say it loudly
4. No-training-on-customer-data default, stated

## Phase 5 — Differentiators & polish (ongoing)
1. Workspace knowledge-graph view polish (exists already — cheap competitors have nothing like it; strongest side-by-side demo asset for consulting/NGO evals)
2. Agentic retrieval mode for complex/multi-hop questions only (retrieval-in-the-loop is the 2026 default pattern; keep simple lookups on the fast path)
3. Mobile-responsive + low-bandwidth pass (African market: 65% of Sub-Saharan Africa offline despite coverage — graceful degradation, small bundles)
4. Consider Claude (Haiku 4.5/Sonnet 5) for chat synthesis — citation faithfulness is the product promise
5. Brand sweep: remaining "Retrievo"/lit-rag names in repo, README, container names

## Explicitly deferred
- GraphRAG expansion beyond current feature (benchmark verdict: complementary, not core — revisit post-Phase 2)
- Multimodal/ColPali ingestion; self-hosted embedding models; Mittelstand/enterprise sales motion; SOC2/ISO (needed only above ~€20k ACV)

## Sequencing logic
Phase 1 before Phase 2: retrieval quality changes need the eval harness to prove the pgvector migration doesn't regress quality. Phase 3 can start once Phase 1's harness exists, in parallel with Phase 2. Revenue features (3) intentionally land before trust paperwork (4) because self-serve academic/Pro buyers don't ask for DPAs — teams do, and Team buyers arrive after the product has references.
