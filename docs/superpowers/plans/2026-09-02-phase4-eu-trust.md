# Phase 4: EU Trust Package — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Checkbox steps.

**Goal:** GDPR-credible deletion that provably purges everything, plus the trust surface German/EU buyers gate on: privacy policy, Impressum, DPA template, sub-processor list, EU-hosting page.

**Architecture:** A. `literature_rag/deletion.py` with `purge_job(db, job)` (vector collection, BM25 pkl, storage objects, knowledge_*/relations/chat/members/invites/documents, job row) and `purge_user(db, user)` (their jobs via purge_job + memberships in others' jobs + invites they created + sessions + tokens + user row); `DELETE /api/auth/me` and the KB delete route both use it (KB delete becomes hard — the UI already promises "permanently delete"). B. Static legal pages in the webapp (`/legal/privacy`, `/legal/impressum`, `/legal/dpa`, `/trust`) with `{{PLACEHOLDER}}` blocks for TheNerdsInt's legal identity; footer links.

**Honesty constraint (non-negotiable):** hosting/storage/DB are EU (Hetzner Falkenstein, Supabase Frankfurt); LLM processing sends document text to **OpenAI (US, embeddings/insights)** and **xAI (US, chat)** under their API no-training terms. The trust page and privacy policy must say this plainly — "data stays in the EU" applies to storage, not LLM inference.

**Spec:** ROADMAP Phase 4. Verified: `_hard_delete_job_for_user` (auth.py:244) misses knowledge_*/relations/members/invites (FK violations proven in manual cleanups); job DELETE route soft-deletes while webapp i18n promises permanent deletion; `DELETE /api/auth/me` exists (auth.py:281).

## Tasks
### Task A: Verified deletion
- [x] `literature_rag/deletion.py`: `purge_job`, `purge_user` (correct FK order, best-effort storage/vector deletion with logged failures, DB deletions transactional)
- [x] Rewire `auth.py /me` (use purge_user) and `jobs.py DELETE /{job_id}` (owner-only; hard purge via purge_job)
- [x] Tests `tests/test_deletion.py`: build a user with job + documents + knowledge rows + member + invite + chat session, purge, assert every table empty for those ids; member-of-someone-else's-job user deletion leaves the job intact minus their membership
- [x] Full suite green; commit `feat: complete GDPR-grade purge for accounts and knowledge bases`
- [x] Deploy; prod-verify: temp user with KB+doc+invite deletes own account via API → DB rows gone (SQL check), MinIO object gone
### Task B: Trust pages
- [x] 4 React pages + footer links; placeholders `{{LEGAL_NAME}} {{ADDRESS}} {{REGISTER}} {{CONTACT_EMAIL}}`; sub-processor table (Hetzner DE, Supabase/AWS Frankfurt, OpenAI US, xAI US, Stripe when added); no-training statement; deletion rights section pointing at account deletion
- [x] Lint+build; ship dist; commit `feat: legal & trust pages (privacy, impressum, DPA, EU hosting)`
- [x] Living docs; plan checkboxes
