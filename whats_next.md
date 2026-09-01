# What's Next

**Original Goal:** Production-grade multi-tenant retrieval/RAG platform (Retrievo), live as **Humbowo** at **humbowo.com** on infrastructure Shaun controls.

## Now
1. Shaun: paste `GROQ_API_KEY` and `OPENAI_API_KEY` into `literature_review_rag_api/.env` (clipboard routine) — chat + document indexing are dormant until then; Claude then ships them to the server and restarts the container
2. Object storage for PDF uploads: create S3-compatible bucket (Cloudflare R2 free tier or Hetzner Object Storage), check storage code for custom-endpoint support, set AWS_* env vars
3. Smoke-test the full user flow in the browser: register → create knowledge base → upload PDF → search → chat
4. Set `REQUIRE_HTTPS=true` in server .env now that TLS is live (defense in depth)

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
- 2026-09-02: **humbowo.com LIVE** — Hetzner cx23 provisioned via API, app deployed, DNS pointed, Let's Encrypt TLS, all security checks pass
- 2026-09-02: Supabase Frankfurt DB live, schema initialized (16 tables), connection verified from app code
- 2026-09-01: Backend made Postgres-ready; CORS/.env prepped; hosting + DB decided; living docs created; state audit after 3.5-month gap
