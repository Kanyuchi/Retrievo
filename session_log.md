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
