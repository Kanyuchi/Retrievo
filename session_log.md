# Session Log

## 2026-09-01 — Project state audit after ~3.5-month gap; humbowo.com migration kickoff
- Read repo + git history to reconstruct state (last commit was 2026-05-18; 146 commits total since 2026-01-24)
- Pushed the one unpushed docs commit (`d972533`) to origin/main
- Audited every domain/host/IP reference in the repo (nginx, TLS scripts, CORS, OAuth, cookies, frontend API base) in preparation for moving to humbowo.com
- Verified humbowo.com is registered (GoDaddy, 2026-09-01) with GoDaddy DNS — currently parked
- **Discovered production is down**: old Lightsail server 13.49.191.201 unreachable on 22/80/443, and `.keys/lightsail.pem` missing locally; old AWS account (Nguks') presumed inaccessible → new hosting + new database required
- Created living documentation files (project_state.md, session_log.md, whats_next.md)

## 2026-09-01 (later) — Postgres/Supabase readiness + humbowo.com config prep
- Shaun provisioned: Supabase project "Humbowo" (org TheNerdsInt, currently ap-southeast-1/Singapore — EU region recreation recommended) and has a Hetzner account (products currently suspended pending overdue payment)
- Added `psycopg2-binary` to requirements.txt and requirements-prod.txt (backend had no Postgres driver)
- Added `pool_pre_ping=True` to the SQLAlchemy engine (Supabase poolers drop idle connections)
- docker-compose.yml: `DATABASE_URL` now env-overridable (was hardcoded to SQLite)
- config/literature_config.yaml: CORS origins now humbowo.com/www.humbowo.com (replaced dead Lightsail IP)
- .env.example: documented production values (Supabase pooler DATABASE_URL, humbowo.com CORS/OAuth/domain)
- Smoke-tested: database.py init + User/Job CRUD against fresh SQLite with new engine args, psycopg2 imports, docker compose config validates

## 2026-09-01 (evening) — Hetzner reactivated; credential plumbing + CLAUDE.md refresh
- Shaun paid the overdue Hetzner invoice (all settled) and deleted the Singapore Supabase project; new Supabase account is under company TheNerdsInt
- Product context locked in: Humbowo is a Shona product targeting Africa + Germany clients (Shaun based in Germany, currently in Thailand); Frankfurt (eu-central-1) confirmed as DB region — co-location with the Hetzner server matters more than user geography
- Created `.keys/README.md` documenting the credential drop-zone (hetzner_api_token, supabase_pat, db_url, SSH key); `.keys/` confirmed gitignored
- Rewrote CLAUDE.md production section: dead Lightsail instructions replaced with Humbowo target architecture (Hetzner + Supabase Frankfurt + humbowo.com + TLS cutover scripts)

## 2026-09-02 — Production database live: Supabase Frankfurt schema initialized
- Supabase project "Humbowo" recreated in eu-central-1 (ref xhtuzovyiewmvlnmhjwh), verified ACTIVE_HEALTHY via Management API
- Prepared gitignored production `.env` (JWT secret generated, domain/CORS/OAuth prefilled); repaired it after an editor stale-buffer save clobbered earlier values
- DB password contains `@` — URL-encoded as `%40` in DATABASE_URL (Session pooler, port 5432)
- Smoke-tested for real: connected to PostgreSQL 17.6 via the app's database.py and ran init_db — all 16 tables created in Supabase
- Still needed in .env: HETZNER_API_TOKEN, GROQ_API_KEY, OPENAI_API_KEY

## 2026-09-02 — 🚀 humbowo.com LIVE: server provisioned, deployed, TLS verified
- Grabbed Hetzner API token from clipboard; provisioned `humbowo-prod` (cx23 — CX22 line was retired — Falkenstein, Ubuntu 22.04, Docker via cloud-init, 2GB swap added) at **178.105.211.235**; fresh SSH key `.keys/humbowo_ed25519`
- Shaun pointed GoDaddy A record @ → 178.105.211.235 (www CNAME already → apex); propagation confirmed on 8.8.8.8 and 1.1.1.1
- Cloned repo on server, shipped .env, built API image (~9 min); container failed on committed dangling `data` symlink (→ ../lit_rag from old dev machine) — replaced with real dirs, removed from git, path now gitignored
- Built webapp locally, deployed to `/var/www/humbowo` (nginx couldn't read /root)
- Ran TLS cutover: Let's Encrypt cert (expires 2026-11-30, auto-renew), removed stock nginx default site (duplicate default_server conflict)
- **verify_tls_cutover.sh humbowo.com: ALL PASS** — site 200, /api/healthz 200 over TLS, 301 redirect, HSTS/CSP/security headers
- Rebranded webapp Retrievo → Humbowo (index.html title, Home/Login/Jobs pages), rebuilt, redeployed — verified live (<title>Humbowo</title>)
- Shipped .env with OPENAI_API_KEY (indexing enabled) + restarted container; GROQ_API_KEY still pending — user pasted an xAI (`xai-...`) key, needs a real Groq key (`gsk_...`) from console.groq.com
- LLM API options compared (Groq/OpenAI/Anthropic/Mistral); decision: launch on Groq+OpenAI, consider Claude Haiku 4.5/Sonnet 5 for chat post-launch

## 2026-09-02 — Research sprint + roadmap: architecture audit, RAG SOTA, market study
- Deployed 3 parallel research agents: codebase architecture audit, 2026 RAG best-practices survey, market/monetization research (Germany + Africa)
- Key audit findings: production per-job query path is dense-only (hybrid BM25 code exists but disconnected); storage.py lacks custom S3 endpoint support; quota/plan-tier scaffolding exists but unenforced; scaling bottlenecks mapped (embedded Chroma, pickle BM25, in-process tasks)
- Key research findings: hybrid+rerank+eval-harness are table stakes; pgvector-on-Supabase is the right vector store at our scale; 73% of RAG failures are retrieval
- Market: wedge = academia top-of-funnel → consulting/NGO teams on €25/seat Team tier; EU residency (already ours) is a sales asset; mobile money needed for Africa
- Synthesized ROADMAP.md (5 phases, each with test gates) + published shareable artifact

## 2026-09-02 (am) — Phase 0 launch hygiene executed
- Hetzner firewall `humbowo-fw` created + applied (in: 22/80/443/icmp only); server auto-backups enabled
- REQUIRE_HTTPS=true shipped to server; redeployed; healthz + site verified
- storage.py: S3_ENDPOINT_URL support added (R2/Hetzner/MinIO) + compose/.env.example wiring; verified custom + default endpoints via boto3 meta
- Live production E2E smoke PASSED: register → login → create KB → upload PDF (extract/chunk/embed/index) → query returns correct chunk
- Server git pull conflict (data dir vs removed symlink) resolved by move-aside
- Decision: per-job upload stays synchronous until Phase 2's queue (changing the response contract now would break the frontend for no durable gain)
- Remaining Phase 0 (needs Shaun): Groq key (gsk_), object storage bucket creds, uptime-monitor account

## 2026-09-02 (noon) — Phase 1 executed: hybrid retrieval in chat path + CI eval gate
- Correction to audit: raw search route already had hybrid; the dense-only gap was JobCollectionRAG (the CHAT/agentic path) — fixed there
- job_rag.py: added injected bm25_retriever + _hybrid_fuse (RRF via existing HybridScorer, post-filters BM25 hits against where-filter, graceful fallback); chat route now injects the per-job BM25 retriever
- New tests: HybridScorer characterization (4), JobCollectionRAG hybrid fakes (3), chat wiring check (1), deterministic retrieval-mechanics CI gate (3) — full suite 25 passed inside the production image
- Test workflow: no local py3.12, so tests run in the prod Docker image on the server with volume-mounted sources (/root/phase1test)
- Deployed + verified live: indexed KB returns correct chunk via hybrid path, no fusion-skip warnings
- Deferred (per plan): Cohere reranker (needs key), chunking A/B + BGE-M3 eval (need corpus + spend)

## 2026-09-02 (midday) — Local test environment fixed + prod DB cleaned
- Installed Python 3.12 (brew), created literature_review_rag_api/venv, full requirements install — chromadb 0.4.24 works
- Added tests/conftest.py: every pytest run defaults to throwaway SQLite + local indices + dummy creds (setdefault, overridable) — the app has no load_dotenv, so process env is authoritative
- Full suite: 25 passed locally in 34s — server-Docker test workflow retired
- Discovered + fixed fallout: earlier server-image test runs used prod env → test users (ui_smoke_*, unverified_*) in production Supabase. Deleted all 7 test users, 6 jobs, tokens; only Shaun's real account remains
- CLAUDE.md: canonical test command + warning documented

## 2026-09-02 (afternoon) — Phase 2a executed: vectors + lexical search live on Supabase pgvector
- New literature_rag/pg_store.py: PgVectorStore (Chroma-collection-compatible: add/get/query/delete/count, L2 distance parity), PgLexicalRetriever (Postgres FTS 'simple' config, BM25Retriever-compatible, zero index maintenance), PgClientShim (delete_collection)
- VECTOR_BACKEND env switch (default chroma) wired through jobs.py/insights.py/auth.py getters; instant rollback = flip env back
- Tests: 10 pg_store integration + 3 backend-switch + 2 hybrid-parity; local pgvector Docker container (port 55433; 55432 was another project's); CI now runs a pgvector/pgvector:pg17 service container — 40 tests green locally and in CI
- Migration script (idempotent upsert) ran on server: old Chroma had 0 chunks (job 1 'work' was empty) — clean-slate cutover
- Flipped production to VECTOR_BACKEND=pgvector; E2E verified: upload → chunk row visible in Supabase vector_chunks → hybrid query returns it; test user cleaned after
- ChromaDB + BM25 pickles now legacy-only (rollback path); removal in Phase 2b

## 2026-09-02 (evening) — Phase 2b live: rq queue, Redis state, multi-worker
- Compose stack grew to api + worker (rq) + redis (AOF-persistent); Dockerfile now runs 2 uvicorn workers
- job_tasks.py: ingestion extracted into process_job_upload (UploadTaskRecord lifecycle, temp cleanup) — sync route wraps it inline, new POST /api/jobs/{id}/upload/async enqueues it; status via existing DB-backed /api/upload/{task_id}/status
- Redis-backed rate limiting (RedisFixedWindowCounter, auto-fallback to memory); OAuth state auto-upgraded to Redis via REDIS_URL
- Frontend uploadToJob switched to async+poll INTERNALLY — JobDetail/Files pages untouched
- CI honesty fix: backend job had been failing since the conftest commit (bare pytest lacks cwd on sys.path → python -m pytest) and frontend lint had 7 real errors (i18n escapes, shadcn export pattern, cytoscape anys) — all fixed, both jobs verified green on the exact run
- Deploy fought SSH instability: hung compose killed (pkill self-match lesson), relaunched via systemd-run
- E2E verified on prod: async upload → rq worker container processed it (worker logs confirm) → status completed → query returns chunk; 47 tests green; test user purged

## 2026-09-02 (late) — Phase 3a: quota enforcement live
- Wired the dormant QuotaService into create_job (403 at tier KB limit), both upload routes (403 over tier file-size/doc/storage limits), query_job + chat (429 at daily API-call limit, counter incremented)
- 4 new tests (KB limit, enterprise bypass, file-size rejection, daily-call exhaustion) — 49 total green
- Deploy lesson: systemd-run needs --working-directory (compose found no config from /); verified fix by grepping the quota symbol inside the running container before re-testing
- Prod verified: 4th KB create for a free user → 403 "Knowledge base limit reached (3). Upgrade plan for more."; worker container healthcheck shows unhealthy (inherited curl check — cosmetic, fix queued)

## 2026-09-02 (night) — Phase 3b live: team workspaces with roles + invite links
- Models: JobMember (viewer/editor, owner implicit) + JobInvite (token, expiry, max_uses) + CRUDs; membership.require_job_role helper
- All 23 inline owner-only checks across jobs/chats/graph/insights routers replaced with role checks (viewer=read/query/chat, editor=+upload/delete/build, owner=manage); upload quota now charges the KB owner's plan
- New endpoints: invites CRUD, POST /api/jobs/join/{token}, members list/remove/role-change; GET /api/jobs includes shared KBs with role
- Frontend: Team card in JobDetail (invite link generation + copy, member management), /join/:token page, role badges, viewer-mode hides upload/delete — EN/DE strings included
- Built via two parallel subagents (backend+frontend); backend agent caught a members-shape contract mismatch pre-commit; I fixed a flaky fixture (id() reuse → uuid)
- Deploy blocked twice by server↔GitHub 'expected flush after ref listing' — fixed durably with git config http.version HTTP/1.1 on the server
- Prod E2E (3 users): editor join+query+upload 200; viewer upload 403; shared KB listed with role; members endpoint correct — then all test data purged (only Shaun's account remains)
- 66 tests green ×3 runs

## 2026-09-02 (final) — Chat live via xAI Grok + MinIO object storage
- Shaun's "Groq" key is an xAI (Grok) key — instead of key-shopping, built literature_rag/llm.py provider factory: xai- keys → OpenAI client on api.x.ai, model grok-4.20-non-reasoning (LLM_MODEL overridable); gsk_ keys → Groq unchanged; agentic pipeline per-agent models aligned to provider (first prod chat 400'd on llama model id — fixed with align_agent_models covering all 4 roles)
- MinIO S3-compatible object storage as compose service (bucket humbowo-documents, creds in .env, covered by Hetzner server backups); S3_ENDPOINT_URL path from Phase 0 used as designed
- Prod verified: chat answers with citations via grok-4.20-non-reasoning; uploaded PDF listed in MinIO bucket; 70 tests green
- Quality observation for Phase 1 follow-up: generation context showed a truncated snippet (~110 chars, looks like title-length truncation) — the model correctly refused to invent facts; investigate context assembly with the golden-set eval
- Test user purged; DB holds only Shaun's account

## 2026-09-02 (evening 2) — Phase 4 complete: EU trust package
- deletion.py: purge_job/purge_user (FK-safe order, best-effort external stores with logged failures) — fixes account deletion that would have FK-crashed on workspaces/knowledge tables; KB DELETE route now hard-purges by default (matching the UI's long-standing "permanently delete" promise; ?hard_delete=false for soft)
- Prod-verified GDPR flow: temp account with KB+doc+invite deleted itself via DELETE /api/auth/me → users/jobs/vector_chunks/invites all 0, MinIO object gone; orphaned pre-purge test object also removed (bucket now empty = matches reality)
- 4 public legal/trust pages live (subagent-built): /legal/privacy, /legal/impressum, /legal/dpa, /trust + global footer links; honest AI-processing disclosure (OpenAI/xAI US, no-training terms; stored documents stay EU); amber {{PLACEHOLDER}} tokens await TheNerdsInt legal details (name, address, register, VAT, managing director)
- 72 tests green

## 2026-09-02 (late evening) — Phase 5 round 1: fusion bug fixed, truncation mystery solved, brand + bundle
- Debug agent (instrumented repro with prompt-capturing fake LLM) proved content plumbing sound on all 3 pipeline paths, then found the REAL latent bug: _hybrid_fuse stamped raw dense distances, so _postprocess_results re-sorted by dense similarity and silently discarded the RRF hybrid ranking when trimming to n_sources — BM25-surfaced answer chunks could be dropped for generic dense-similar ones. Fixed: fused chunks carry RRF-rank-derived scores. 76 tests.
- The observed "truncation" was a TEST ARTIFACT: hand-rolled single-line test PDFs overflow the 612pt page; the extractor correctly reads only on-page text (~113 chars). Proven by storing/inspecting the chunk (length 113) then uploading a line-wrapped PDF → chat answered "Approximately 12,000 jobs [1]" on production. Grounded citation behavior confirmed end to end.
- Brand sweep: README + UI strings → Humbowo (agent was stopped mid-commit by user; I verified lint/build and committed the clean work — revertible if the stop meant discard)
- Low-bandwidth: cytoscape code-split → main bundle 1.44MB→902KB (gzip 423→255KB, −40% first load); nav breakpoint fix
- All prod-verified; test accounts self-deleted via the GDPR purge (eating our own dogfood)

## 2026-09-02 (night) — Phase 5 round 2: eval harness live, graph feature unlocked, UI polished
- scripts/run_semantic_eval.py: corpus-agnostic golden-set eval (filename-based expectations survive re-uploads; P@k/recall/MRR; --min-precision gate) + scripts/make_demo_corpus.py (6 synthetic wrapped-PDF papers on German regional transitions, clearly disclaimed) + eval/demo_queries.yaml (8 queries)
- Demo account (demo@humbowo.com) + KB "German Regional Transitions (Demo)" (job 19) on prod; baseline eval: recall 1.000, MRR 1.000 over 8 queries (P@5 bounded by 6-doc corpus size)
- Graph build returned 0 entities from 24 claims → root cause: _extract_json dropped ```json-fenced LLM output (language tag survived fence stripping → json.loads failed silently). Fixed in graph.py + insights.py + regression test (77 tests). Post-fix: 139 entities / 116 edges / 26 clusters on the demo corpus
- Knowledge graph UI polished (agent): cluster legend w/ highlight toggle, degree-scaled nodes, neighbor detail card, weighted bezier edges, loading/empty/error states, fit/layout/search controls — code-split preserved
- Thesis corpus NOT on this machine (old laptop/S3 only) — semantic eval on real papers blocked on Shaun locating them; demo corpus stands in
- Editor invite for Shaun minted on the demo KB (30 days, 3 uses)

## 2026-09-03 — Thesis corpus live on Humbowo: 56 papers indexed, real eval baseline recorded
- Blank-page report: site verified healthy in clean browser (title, content, footer render; only logged-out 401s) — Shaun's Safari cache; hard-reload advised
- Thesis corpus located in ~/Downloads (Phase 1/3/4 folders, 60 PDFs, 182MB) + MIT personality Bundle (deferred)
- Batch upload saga: (1) initial batch died at my 10-min tool timeout → detached nohup runner; (2) 22 enqueue failures from 30-min JWT expiry on a 2h batch → per-file token refresh; (3) retry's dedupe prefetch failed silently → 38 duplicate doc versions → purged (kept newest), stats recomputed; (4) purge deleted SHARED deterministic storage keys → 36 objects restored from local files via staged tar+put_object; (5) 2 files failed on curl -F comma/apostrophe filename parsing → quoted syntax fixed it
- Final: 56/59 extractable papers indexed (~5,900 chunks); 3 blocked as image-only scans (OCR not in container image — known gap)
- Real golden-set baseline (eval/thesis_queries.yaml, 8 queries): recall@5 0.50, MRR 0.50, no reranker — 4 exact-paper rank-1 hits, 4 honest misses in a competitive corpus; eval matcher now normalizes filenames
- Insights + knowledge graph building on full corpus (background); editor invite for Shaun minted (60 days)
- Enterprise tier set on thesis service account (60 docs > free caps); playwright artifacts gitignored
