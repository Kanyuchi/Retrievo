# What's Next

**Original Goal:** Production-grade multi-tenant retrieval/RAG platform (Retrievo), live as **Humbowo** at **humbowo.com** on infrastructure Shaun controls.

## Now
1. Retrieval quality vs baseline (recall@5 0.50/MRR 0.50 on thesis corpus): Cohere reranker (needs key), chunking A/B — measured via scripts/run_semantic_eval.py
2. Add OCR (tesseract) to Docker image for the 3 image-only scans; batch-uploader hardening lessons → future bulk-import feature
2. Shaun: TheNerdsInt legal details (name, legal form, address, register court+number, VAT ID, managing director) → fill {{PLACEHOLDER}} tokens in legal pages
3. Phase 3c (billing) when Stripe account exists; then Phase 5 differentiators (graph polish, low-bandwidth pass, chunking A/B with golden set)
3. Phase 3c (billing): Stripe checkout/webhooks/portal + billing page — BLOCKED on Shaun creating the Stripe account (pricing locked: Free / €19 Pro / €25-seat Team, 3-seat min, academic discount); Paystack after
4. Uptime monitoring (UptimeRobot or similar, needs account) on https://humbowo.com/api/healthz

## Soon
- Consider Claude Haiku 4.5 / Sonnet 5 for chat synthesis (best citation faithfulness; Groq free tier is the launch default)
- Hetzner firewall via API (allow 22/80/443 only)
- Server backups: Hetzner auto-backup (~20% of server cost) or snapshot cadence
- Google/GitHub OAuth apps for humbowo.com (redirect URIs) if social login wanted
- Update README.md branding (Retrievo → Humbowo) and REPLICATION_GUIDE.md
- Uptime monitoring (e.g. UptimeRobot free) on https://humbowo.com/api/healthz

## Later
- Migrate webapp title/branding, favicon, i18n strings to Humbowo
- Delete webapp-backup/ and litrag_webapp_pic/ directories
- CI/CD: GitHub Action to deploy on push to main

## Blocked
- (nothing)

## Done
- 2026-09-03: Thesis corpus (56 papers) live in "Thesis Literature — Regional Transitions" KB; real eval baseline recall@5 0.50 / MRR 0.50; insights+graph built; invite minted
- 2026-09-02: Phase 5 round 2 — semantic eval harness (recall 1.0/MRR 1.0 baseline on demo corpus), json-fence parse fix unlocking knowledge graph (0→139 entities), graph UI polish shipped
- 2026-09-02: Phase 5 round 1 — latent hybrid-ranking bug fixed (RRF preserved through trim); "truncation" root-caused as test-PDF artifact, grounded-citation chat verified with real figure; Humbowo brand sweep; −40% main bundle (cytoscape code-split)
- 2026-09-02: Phase 4 — GDPR-grade purge (verified live), legal pages (privacy/Impressum/DPA/trust) with honest AI-processing disclosure
- 2026-09-02: Chat LIVE via xAI Grok (provider factory); MinIO object storage live (uploads verifiably in bucket) — every core feature of the product now works in production
- 2026-09-02: Phase 3b — team workspaces (roles viewer/editor/owner, invite links, member management) live and E2E-verified on prod
- 2026-09-02: Phase 3a — plan-tier quotas enforced (KB/upload/API-call) and verified on prod
- 2026-09-02: Phase 2b — rq ingestion queue + worker container, Redis rate-limit/OAuth state, 2 uvicorn workers, async job uploads (frontend polling); CI repaired and verified green
- 2026-09-02: Phase 2a — vectors + FTS live on Supabase pgvector behind VECTOR_BACKEND switch; CI parity gate with pgvector service container
- 2026-09-02: Local py3.12 test env + conftest isolation; prod DB purged of test users; Phase 1 (hybrid chat retrieval + CI gate) deployed
- 2026-09-02: **humbowo.com LIVE** — Hetzner cx23 provisioned via API, app deployed, DNS pointed, Let's Encrypt TLS, all security checks pass
- 2026-09-02: Supabase Frankfurt DB live, schema initialized (16 tables), connection verified from app code
- 2026-09-01: Backend made Postgres-ready; CORS/.env prepped; hosting + DB decided; living docs created; state audit after 3.5-month gap
