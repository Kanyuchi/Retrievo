# Phase 6: Bulk Import + Workspace-Backed Public Demo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Checkbox steps.

**Goal:** (A) A first-class bulk-import experience encoding every uploader-saga lesson; (B) the "Public Demo Collection" becomes real public workspaces (demo jobs 19 & 21), retiring the dead legacy global collection from the product surface.

## Part A — Bulk import (frontend-only; backend already supports it)
The per-file async endpoint + DB-backed status polling + queue + 401-retry interceptor + cookie-auth all exist. Bulk import is client orchestration in `JobDetail.tsx`'s upload dialog:
- Multi-file select (exists) upgraded to an import queue table: filename, size, status chip (queued / uploading / indexing / done / failed / skipped-duplicate), per-file error text
- **Dedupe**: before starting, fetch `GET /api/jobs/{id}/documents` and mark files whose name matches an existing `filename`/`original_filename` (normalize: lowercase, non-alnum→_) as skipped-duplicate (override checkbox "re-import duplicates")
- **Concurrency 2**, continue-on-error, per-file Retry button on failures, Cancel-remaining button
- Summary line on completion (X imported · Y skipped · Z failed) via toast + inline
- i18n EN/DE for new strings

## Part B — Public workspaces (backend + frontend)
### Backend
- `Job.is_public` bool column (default false) + migration in `database.py._run_migrations` (ALTER TABLE ADD COLUMN pattern — `create_all` cannot add columns to existing tables)
- `membership.get_job_role`: return "viewer" for `job.is_public` when the user has no explicit role (INCLUDING anonymous user_id=None)
- Anonymous read access on job READ routes: query, chat, documents list/download, graph read, insights read, members list → switch `Depends(get_current_user)` to `Depends(get_current_user_optional)` (exists in auth.py) and pass `user.id if user else None` into `require_job_role`; write routes unchanged (strict auth). API-call quota: skip increment when anonymous (rate limiter covers abuse).
- `GET /api/jobs` (list): include public jobs for everyone — anonymous callers get ONLY public jobs (route becomes optional-auth); role field "viewer" unless owner/member. Mark payload `is_public: true`.
- Admin toggle: `PATCH /api/jobs/{id}` gains optional `is_public` (owner only).
- Tests: anonymous can query/chat-read a public job (TestClient, no auth header); anonymous 401/403 on private job and on ANY write; public jobs appear in anonymous /api/jobs.
- Ops (operator, after deploy): `UPDATE jobs SET is_public=true WHERE id IN (19, 21);`

### Frontend
- KB switcher: replace the legacy "Public Demo Collection" pseudo-entry with real public jobs from /api/jobs (label "Demo" badge via is_public); anonymous users see them too
- Home page: stats tiles read the selected/first public job's `/api/jobs/{id}/stats`-equivalent (document_count/chunk_count from the jobs payload) instead of legacy `/api/stats`; remove the legacy double-fetch
- Dataset, Files, Search, Chat pages: when a public job is selected, use the job-scoped endpoints (`/api/jobs/{id}/documents`, `/query`, `/chat`) — the same code path as own KBs; delete/upload controls hidden for viewer role (existing role logic)
- Remove remaining legacy-endpoint calls (`/api/stats`, `/api/papers`, `/api/search`, `/api/chat`, `/api/documents`, `/api/upload*` global) from the frontend; legacy backend routes stay (deprecated, graceful) for API compat
- i18n strings, lint+build green

## Verification gates
- Suite green (backend: 84+ tests); anonymous-access tests included
- Browser (Playwright): anonymous visit → switcher shows demo workspaces → Dataset lists demo papers → Chat answers with citations → thesis-style workspace pages still gated
- Deploy; mark jobs 19/21 public; audit-style spot-check of Home/Dataset/Chat/Search anonymous flows
