# What's Next

**Original Goal:** Production-grade multi-tenant retrieval/RAG platform (Retrievo), now to be served at **humbowo.com** on infrastructure Shaun controls.

## Now
1. Decide + provision new hosting (old Lightsail under third-party AWS account is dead) — needs Shaun's input on provider/account
2. Decide + provision the new database (SQLite-on-volume vs managed Postgres) — needs Shaun's input
3. Create new S3 bucket (or equivalent object storage) under Shaun's account; set AWS creds in server `.env`
4. Point GoDaddy DNS A record for humbowo.com (+ www) at the new server IP
5. Run TLS cutover (`scripts/deploy/cutover_host_nginx_tls.sh humbowo.com <email>`) and verify (`scripts/security/verify_tls_cutover.sh humbowo.com`)

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
- 2026-09-01: State audit after gap; domain/host reference map for migration
- 2026-09-01: humbowo.com registered (GoDaddy) and confirmed under our DNS control
- 2026-09-01: Living docs created; unpushed commit pushed
