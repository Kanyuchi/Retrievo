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
- LLM API options compared (Groq/OpenAI/Anthropic/Mistral); decision: launch on Groq+OpenAI, consider Claude Haiku 4.5/Sonnet 5 for chat post-launch
