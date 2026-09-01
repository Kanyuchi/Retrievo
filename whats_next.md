# What's Next

**Original Goal:** Production-grade multi-tenant retrieval/RAG platform (Retrievo), now to be served at **humbowo.com** on infrastructure Shaun controls.

## Now
1. Shaun: recreate Supabase project "Humbowo" in **eu-central-1 (Frankfurt)** under TheNerdsInt; drop the Session-pooler string into `.keys/db_url` and a personal access token into `.keys/supabase_pat`
2. Shaun: drop a Hetzner Cloud API token (Read & Write) into `.keys/hetzner_api_token`
3. Claude: provision Hetzner server via API (CX22, Ubuntu 22.04, Falkenstein/Nuremberg), install Docker, deploy app with Supabase `DATABASE_URL`
4. Object storage: create bucket (Cloudflare R2 or Hetzner Object Storage, S3-compatible) and set S3 env vars — check storage code for custom-endpoint support
5. Point GoDaddy DNS A records (@ and www) for humbowo.com at the new Hetzner IP, then run TLS cutover (`scripts/deploy/cutover_host_nginx_tls.sh humbowo.com <email>`) and verify (`scripts/security/verify_tls_cutover.sh humbowo.com`)

## Soon
- Update server `.env`: `CORS_ORIGINS`, `OAUTH_REDIRECT_BASE`, `OAUTH_REDIRECT_URL`, `AUTH_COOKIE_DOMAIN`, S3 + JWT secrets
- Update `config/literature_config.yaml` CORS origins (replace old IP 13.49.191.201 with https://humbowo.com)
- Update Google Cloud Console + GitHub OAuth redirect URIs to humbowo.com
- Rebuild indices / re-upload seed corpus (old ChromaDB indices + S3 PDFs presumed lost)
- Update project CLAUDE.md deploy section (server IP, key path) once new server exists
- Store new SSH key at `.keys/` per dependency-management rule

## Later
- If moving to managed Postgres: write migration path from SQLite schema (SQLAlchemy models) + data seeding
- Re-evaluate webapp-backup/ and litrag_webapp_pic/ directories for deletion
- Revisit REPLICATION_GUIDE.md accuracy after the rebuild

## Blocked
- Recovery of old production data (user DB, S3 PDFs `lit-rag-flow`, indices) — blocked on whether anyone can still access Nguks' AWS account

## Done
- 2026-09-01: Backend made Postgres-ready (psycopg2 dep, pool_pre_ping, env-overridable DATABASE_URL) + CORS/.env.example prepped for humbowo.com — smoke-tested
- 2026-09-01: Hosting decided (Hetzner) + database decided (Supabase managed Postgres); Supabase project created
- 2026-09-01: State audit after gap; domain/host reference map for migration
- 2026-09-01: humbowo.com registered (GoDaddy) and confirmed under our DNS control
- 2026-09-01: Living docs created; unpushed commit pushed
