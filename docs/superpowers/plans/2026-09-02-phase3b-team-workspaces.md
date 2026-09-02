# Phase 3b: Team Workspaces (Members, Roles, Invite Links) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Checkbox steps.

**Goal:** Knowledge bases become shareable workspaces: an owner invites people via link; members get `viewer` (read/query/chat) or `editor` (+upload/delete docs, build insights/graph) access; owner keeps management. This is THE differentiator feature per market research and what Team pricing sells.

**Architecture:** Two new tables (`job_members`, `job_invites`). One helper `require_job_role(db, job, user_id, min_role)` (role order viewer<editor<owner; job.user_id is implicit owner) replaces all 23 inline `job.user_id != current_user.id` checks, each mapped to the weakest sufficient role. Invite links: owner mints a token (role, expiry, max uses); any authed user hitting `POST /api/jobs/join/{token}` becomes a member. `GET /api/jobs` returns owned + member KBs with a `role` field. Upload quota charges the job OWNER's plan; API-call quota stays on the caller.

**Decisions (Shaun, 2026-09-02):** invite links (no email provider); pricing locked separately; Stripe deferred to 3c.

**Spec:** ROADMAP Phase 3 item "Team workspaces with roles". Verified: ownership checks — jobs.py×13, chats.py×5, graph.py×3, insights.py×2; `Job.user_id` FK exists; init_db `create_all` auto-creates new tables on boot (covers prod migration).

## Role mapping (weakest sufficient role per route)
- **viewer**: query, chat, list/download documents, related docs, graph read, insights read, chat sessions (own sessions only — chats stay per-user)
- **editor**: upload (sync+async), delete document, insights run, graph build, term-map updates
- **owner**: job update/delete, invites CRUD, member list/remove/role-change (member LIST is viewer — people may see who's in the room)

## Tasks
### Task 1: Models + membership helper + tests
- Models in `database.py`: `JobMember(id, job_id FK, user_id FK, role str default "viewer", created_at, UniqueConstraint(job_id, user_id))`, `JobInvite(id, job_id FK, token str unique index, role str, created_by FK users, expires_at, max_uses int default 10, use_count int default 0, created_at)` + `JobMemberCRUD` (get_role, add, list_for_job, remove, list_job_ids_for_user) + `JobInviteCRUD` (create with `secrets.token_urlsafe(24)`, get_valid_by_token — checks expiry+uses, consume increments, list_for_job, delete)
- New `literature_rag/membership.py`: `ROLE_ORDER = {"viewer": 1, "editor": 2, "owner": 3}`; `get_job_role(db, job, user_id)`; `require_job_role(db, job, user_id, min_role)` raising 403 HTTPException ("Access denied")
- Tests `tests/test_membership.py`: owner implicit role; member roles; require raises correctly; invite create/validate/expiry/max-uses consume
- [x] Commit `feat: job membership + invite models and role helper`

### Task 2: Replace 23 ownership checks per role mapping
- jobs.py/chats.py/graph.py/insights.py: each `if job.user_id != current_user.id: raise ...` block → `require_job_role(db, job, current_user.id, "<mapped role>")`. chats.py: keep session-owner checks for sessions themselves (sessions are personal) — only the JOB access check loosens to viewer.
- Upload quota: in both upload routes change `check_quota_for_upload(current_user.id, ...)` → `check_quota_for_upload(job.user_id, ...)` (owner's plan pays for storage).
- `GET /api/jobs` (list route): return owned + member jobs, each item gains `"role"`. `JobCRUD.get_user_jobs` extended or route composes: owned (role=owner) + `JobMemberCRUD.list_job_ids_for_user` fetched jobs (their role).
- Tests `tests/test_workspace_access.py` (TestClient): owner invites → second user joins via token → viewer can query but NOT upload (403); editor invite → can upload; non-member 403 on query; member sees KB in their /api/jobs list with role.
- [x] Commit `feat: role-based workspace access on all job routes`

### Task 3: Invite + member routes
- In jobs.py: `POST /{job_id}/invites` (owner; body {role, expires_days=14, max_uses=10}) → {token, join_url: f"https://humbowo.com/join/{token}", role, expires_at}; `GET /{job_id}/invites` (owner); `DELETE /{job_id}/invites/{invite_id}` (owner); `POST /join/{token}` (any authed; consume + add member; idempotent if already member; owner joining = no-op) → {job_id, name, role}; `GET /{job_id}/members` (viewer) → owner + members with emails/names/roles; `DELETE /{job_id}/members/{user_id}` (owner; cannot remove owner); `PATCH /{job_id}/members/{user_id}` (owner; body {role}).
- NOTE route ordering: `/join/{token}` must be declared BEFORE `/{job_id}` catch-alls or use distinct prefix — declare it early in the router.
- Tests folded into test_workspace_access.py (join flow, remove member loses access, invite expiry 403/410).
- [x] Commit `feat: invite-link and member management endpoints`

### Task 4: Frontend
- `api.ts`: createInvite, joinWorkspace, listMembers, removeMember + Job type gains `role?`
- `JobDetail.tsx`: "Team" card (visible to owner): generate invite link (role selector, copy button), member list with remove. Viewer/editor visitors: hide upload/delete controls when `role === "viewer"`.
- New page `JoinWorkspace.tsx` at route `/join/:token`: if authed → call join → redirect to the KB; if not → redirect to login with returnTo.
- `Jobs.tsx`: show role badge on shared KBs.
- Lint + build green.
- [x] Commit `feat: workspace sharing UI (invite links, members, role badges)`

### Task 5: Deploy + verify + docs
- Push; server deploy via systemd-run with --working-directory; healthz.
- Prod E2E: user A creates KB + editor invite; user B joins via token, uploads doc; viewer role blocks upload; cleanup both users.
- Ship frontend dist; living docs; plan checkboxes.
- [x] Commit `docs: Phase 3b complete`

## Notes
- Chat sessions remain personal (user_id-scoped) even inside shared KBs — sharing chat history is a later feature.
- Knowledge insights/graph data is job-scoped, so members see shared results automatically.
- Quota subtlety: owner pays storage/docs; caller pays their own daily API calls — matches seat-pricing intuition.
