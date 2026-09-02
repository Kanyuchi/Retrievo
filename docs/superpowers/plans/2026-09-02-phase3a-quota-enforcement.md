# Phase 3a: Quota Enforcement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Checkbox steps.

**Goal:** The plan-tier quota system (`quotas.py` — complete but never called) actually gates knowledge-base creation, uploads, and query/chat API calls.

**Architecture:** Imperative calls to the existing raise-on-violation helpers (`check_quota_for_kb_creation` 403, `check_quota_for_upload` 403, `check_quota_for_api_call` 429) inside the routes, after auth/ownership checks; query/chat also increment the daily counter via `QuotaService.increment_api_calls`. Tiers: free (3 KBs / 50 docs / 100MB / 500 calls/day / 10MB file), pro, enterprise (unlimited) — values unchanged in this phase; pricing decisions may retune them later.

**Spec:** `ROADMAP.md` Phase 3 item 1. Wire points verified: `routers/jobs.py` create_job (line ~329), upload_to_job, upload_to_job_async, query_job (~843), chat route (~1150).

## Tasks
### Task 1: Wire enforcement + tests
- [x] create_job: `check_quota_for_kb_creation(current_user.id)` after auth
- [x] upload_to_job + upload_to_job_async: `check_quota_for_upload(current_user.id, len(contents))` after size read
- [x] query_job + job chat route: `check_quota_for_api_call(current_user.id)` then `get_quota_service().increment_api_calls(current_user.id)`
- [x] Tests (`tests/test_quota_enforcement.py`): free user hits KB limit at 4th create (403 with quota message); tiny `max_file_size_bytes` monkeypatch → upload 403; `api_calls_today` set to limit in DB → query 429; enterprise user (plan_tier updated in DB) bypasses KB limit
- [x] Full suite green; commit `feat: enforce plan-tier quotas on KB creation, uploads, and queries`

### Task 2: Deploy + verify
- [x] Push, server pull + `docker compose up -d --build api worker` (code-only: cache-fast)
- [x] Prod check: healthz; free-tier KB limit enforced via curl (create 4 KBs on temp user → 4th 403); cleanup temp user
- [x] Living docs + plan checkboxes
