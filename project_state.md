# Retrievo — Project State

_Last updated: 2026-09-02_

## What the project is
Retrievo — a multi-tenant retrieval/RAG platform (FastAPI + ChromaDB backend, React/Vite webapp). Originally built as a literature-review RAG for German regional economic transitions research (13,578 chunks / 83 papers), later generalized into a product with user knowledge bases, chat sessions, EN/DE i18n, knowledge graph (GraphRAG), and knowledge insights.

## What works (as of last active development, 2026-05-18)
- Backend: FastAPI on port 8001, JWT auth (+ optional verified-account enforcement), job-scoped knowledge bases, hybrid retrieval (BM25 + dense), chat sessions with persistence/export, knowledge insights (claims + gaps), knowledge graph with clusters (GraphRAG phase C1), Google Drive OAuth data source
- Frontend: React/Vite webapp, EN/DE i18n, Cytoscape knowledge graph UI, domain-agnostic API base (uses `window.location.origin` when `VITE_API_URL` is empty)
- CI: GitHub Actions workflow for backend smoke + frontend checks
- Security hardening: HTTPS/HSTS handling, path-based rate limits, auth regression tests, host-nginx TLS cutover automation (`scripts/deploy/cutover_host_nginx_tls.sh`) + verification (`scripts/security/verify_tls_cutover.sh`)

## Production (LIVE since 2026-09-02)
- **https://humbowo.com** — Hetzner cx23 `humbowo-prod` 178.105.211.235 (Falkenstein), host nginx + Let's Encrypt (auto-renew), Docker container `lit-rag-api`
- **DB**: Supabase Postgres 17.6, Frankfurt (ref xhtuzovyiewmvlnmhjwh), Session pooler, 16 tables initialized
- **Pending**: GROQ/OPENAI keys (chat + indexing dormant), object storage bucket for uploads
- Credentials: server `.env` (gitignored) + `.keys/` (SSH key `humbowo_ed25519`)

## Old infrastructure (dead, discovered 2026-09-01)
- **Production is DOWN.** Old Lightsail server 13.49.191.201 does not respond on 22/80/443.
- **SSH key `.keys/lightsail.pem` is missing locally** — no access to the old server even if it exists.
- Old AWS resources (Lightsail instance, S3 bucket `lit-rag-flow` in eu-north-1) were under a third-party account (Nguks') — presumed inaccessible. Production data (user DB SQLite, uploaded PDFs in S3, ChromaDB indices) presumed lost unless that account can be recovered.
- Project CLAUDE.md deploy instructions reference the dead server — stale.

## Testing
- Local canonical: `./venv/bin/python -m pytest -q tests` (py3.12 venv, 25 tests) with conftest.py isolation (throwaway SQLite; never prod)
- CI: same suite via GitHub Actions; retrieval-mechanics tests gate deploys

## Key decisions
- 2026-09-01: New domain **humbowo.com** acquired (GoDaddy, registered 2026-09-01, GoDaddy DNS `domaincontrol.com` nameservers). Will replace IP-only / old-domain hosting.
- Database was SQLite in a Docker volume (`DATABASE_URL=sqlite:///./data/db/literature_rag.db`); a new database is planned as part of the infrastructure rebuild (provider TBD).
- Frontend intentionally domain-agnostic (empty `VITE_API_URL` in `.env.production`) — no frontend changes needed for the domain move.

## Infra facts needed for the humbowo.com cutover (from repo audit)
- nginx `server_name` currently `_` in `literature_review_rag_api/nginx/nginx.conf`; host TLS script takes domain as a parameter
- CORS origins: `literature_review_rag_api/config/literature_config.yaml` lines ~300–306 (currently localhost + old IP) and `CORS_ORIGINS` env var
- OAuth: `OAUTH_REDIRECT_BASE` / `OAUTH_REDIRECT_URL` env vars + Google Cloud / GitHub console redirect URIs must be updated to the new domain
- Cookies: `AUTH_COOKIE_DOMAIN` env (empty = auto-scope; `.humbowo.com` for subdomains)
