"""Team workspace access: role-based checks (Task 2) + invites/members (Task 3).

The first block of tests grants membership directly via JobMemberCRUD to
isolate the route-level require_job_role() enforcement (Task 2) from the
invite-link/member-management HTTP endpoints (Task 3), which are covered
by the tests further down using the real invite -> join flow.

Registers a small fixed pool of users (module-scoped) rather than one per
test: /api/auth/register and /api/auth/login share a 15-req/60s rate-limit
bucket keyed by client IP across the WHOLE test session, and other test
files already spend part of that budget.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


def _register(client, email):
    r = client.post("/api/auth/register", json={
        "email": email, "password": "Passw0rd!x", "name": email.split("@")[0]})
    tok = (r.json().get("access_token")
           or client.post("/api/auth/login", json={
               "email": email, "password": "Passw0rd!x"}).json()["access_token"])
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def ws_client():
    from literature_rag.api import app
    return TestClient(app)


@pytest.fixture(scope="module")
def owner_h(ws_client):
    headers = _register(ws_client, "ws-owner@test.local")
    # Owner creates several KBs across this module's tests; bypass the
    # free-tier KB-count quota so that isn't what the tests are exercising.
    from literature_rag.database import get_db_session, UserCRUD
    db = get_db_session()
    user = UserCRUD.get_by_email(db, "ws-owner@test.local")
    user.plan_tier = "enterprise"
    db.commit()
    return headers


@pytest.fixture(scope="module")
def member_h(ws_client):
    return _register(ws_client, "ws-member@test.local")


@pytest.fixture(scope="module")
def stranger_h(ws_client):
    return _register(ws_client, "ws-stranger@test.local")


@pytest.fixture(scope="module")
def owner_user_id():
    from literature_rag.database import get_db_session, UserCRUD
    db = get_db_session()
    return UserCRUD.get_by_email(db, "ws-owner@test.local").id


def _create_job(ws_client, owner_h, name):
    r = ws_client.post("/api/jobs", json={"name": name}, headers=owner_h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _grant_membership(job_id, email, role):
    from literature_rag.database import get_db_session, UserCRUD, JobMemberCRUD
    db = get_db_session()
    user = UserCRUD.get_by_email(db, email)
    JobMemberCRUD.add(db, job_id, user.id, role=role)


def _create_invite(ws_client, owner_h, job_id, role, **kwargs):
    payload = {"role": role, **kwargs}
    r = ws_client.post(f"/api/jobs/{job_id}/invites", json=payload, headers=owner_h)
    assert r.status_code == 200, r.text
    return r.json()


def test_editor_member_can_query_and_upload(ws_client, owner_h, member_h, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    jid = _create_job(ws_client, owner_h, "role-editor-kb")
    _grant_membership(jid, "ws-member@test.local", "editor")

    q = ws_client.get(f"/api/jobs/{jid}/query",
                      params={"question": "anything", "n_sources": 1}, headers=member_h)
    assert q.status_code == 200, q.text

    with patch("literature_rag.job_tasks._ingest_pdf_to_job",
               return_value={"success": True, "doc_id": "d1", "chunks_indexed": 1}):
        up = ws_client.post(f"/api/jobs/{jid}/upload/async", headers=member_h,
                            files={"file": ("t.pdf", b"%PDF-1.4 x", "application/pdf")},
                            data={"phase": "P1", "topic": "T"})
    assert up.status_code == 200, up.text


def test_viewer_member_can_query_but_not_upload(ws_client, owner_h, member_h, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    jid = _create_job(ws_client, owner_h, "role-viewer-kb")
    _grant_membership(jid, "ws-member@test.local", "viewer")

    q = ws_client.get(f"/api/jobs/{jid}/query",
                      params={"question": "anything", "n_sources": 1}, headers=member_h)
    assert q.status_code == 200, q.text

    up = ws_client.post(f"/api/jobs/{jid}/upload/async", headers=member_h,
                        files={"file": ("t.pdf", b"%PDF-1.4 x", "application/pdf")},
                        data={"phase": "P1", "topic": "T"})
    assert up.status_code == 403, up.text


def test_non_member_query_forbidden(ws_client, owner_h, stranger_h):
    # stranger_h may already be a *member* of other jobs created elsewhere
    # in this module, but membership is per-job: on a brand new job they
    # never joined, they must still be forbidden.
    jid = _create_job(ws_client, owner_h, "private-kb")

    q = ws_client.get(f"/api/jobs/{jid}/query",
                      params={"question": "anything", "n_sources": 1}, headers=stranger_h)
    assert q.status_code == 403, q.text


def test_member_sees_shared_kb_with_role_in_job_list(ws_client, owner_h, member_h):
    jid = _create_job(ws_client, owner_h, "listed-kb")
    _grant_membership(jid, "ws-member@test.local", "editor")

    listing = ws_client.get("/api/jobs", headers=member_h)
    assert listing.status_code == 200, listing.text
    matching = [j for j in listing.json()["jobs"] if j["id"] == jid]
    assert len(matching) == 1
    assert matching[0]["role"] == "editor"

    owner_listing = ws_client.get("/api/jobs", headers=owner_h)
    owner_jobs = [j for j in owner_listing.json()["jobs"] if j["id"] == jid]
    assert len(owner_jobs) == 1
    assert owner_jobs[0]["role"] == "owner"


def test_upload_quota_charged_to_job_owner_not_member(ws_client, owner_h, member_h, tmp_path, monkeypatch):
    """check_quota_for_upload now checks job.user_id (the owner's plan), not
    the uploading member's - a member's own tiny quota must not block them
    from uploading into an owner's KB with headroom."""
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    jid = _create_job(ws_client, owner_h, "quota-owner-pays-kb")
    _grant_membership(jid, "ws-member@test.local", "editor")

    from literature_rag.quotas import QUOTA_LIMITS, PlanTier
    original = QUOTA_LIMITS[PlanTier.FREE].max_file_size_bytes
    QUOTA_LIMITS[PlanTier.FREE].max_file_size_bytes = 10  # member's own tier would reject this
    try:
        with patch("literature_rag.job_tasks._ingest_pdf_to_job",
                   return_value={"success": True, "doc_id": "d2", "chunks_indexed": 1}):
            up = ws_client.post(f"/api/jobs/{jid}/upload/async", headers=member_h,
                                files={"file": ("t.pdf", b"%PDF-1.4 bigger than ten bytes", "application/pdf")},
                                data={"phase": "P1", "topic": "T"})
        assert up.status_code == 200, up.text
    finally:
        QUOTA_LIMITS[PlanTier.FREE].max_file_size_bytes = original


# ============================================================================
# Task 3: invite links + member management endpoints
# ============================================================================

def test_editor_invite_join_query_and_upload(ws_client, owner_h, member_h, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    jid = _create_job(ws_client, owner_h, "invite-editor-kb")

    inv = _create_invite(ws_client, owner_h, jid, "editor", expires_days=14, max_uses=10)
    token = inv["token"]
    assert inv["role"] == "editor"
    assert inv["join_url"] == f"https://humbowo.com/join/{token}"
    assert inv["expires_at"] is not None

    joined = ws_client.post(f"/api/jobs/join/{token}", headers=member_h)
    assert joined.status_code == 200, joined.text
    body = joined.json()
    assert body["job_id"] == jid
    assert body["role"] == "editor"

    # Joining again is idempotent and does not consume another use.
    rejoined = ws_client.post(f"/api/jobs/join/{token}", headers=member_h)
    assert rejoined.status_code == 200, rejoined.text
    assert rejoined.json()["role"] == "editor"

    q = ws_client.get(f"/api/jobs/{jid}/query",
                      params={"question": "anything", "n_sources": 1}, headers=member_h)
    assert q.status_code == 200, q.text

    with patch("literature_rag.job_tasks._ingest_pdf_to_job",
               return_value={"success": True, "doc_id": "d3", "chunks_indexed": 1}):
        up = ws_client.post(f"/api/jobs/{jid}/upload/async", headers=member_h,
                            files={"file": ("t.pdf", b"%PDF-1.4 x", "application/pdf")},
                            data={"phase": "P1", "topic": "T"})
    assert up.status_code == 200, up.text


def test_viewer_invite_join_query_ok_upload_forbidden(ws_client, owner_h, stranger_h, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    jid = _create_job(ws_client, owner_h, "invite-viewer-kb")

    inv = _create_invite(ws_client, owner_h, jid, "viewer")
    token = inv["token"]

    joined = ws_client.post(f"/api/jobs/join/{token}", headers=stranger_h)
    assert joined.status_code == 200, joined.text
    assert joined.json()["role"] == "viewer"

    q = ws_client.get(f"/api/jobs/{jid}/query",
                      params={"question": "anything", "n_sources": 1}, headers=stranger_h)
    assert q.status_code == 200, q.text

    up = ws_client.post(f"/api/jobs/{jid}/upload/async", headers=stranger_h,
                        files={"file": ("t.pdf", b"%PDF-1.4 x", "application/pdf")},
                        data={"phase": "P1", "topic": "T"})
    assert up.status_code == 403, up.text


def test_owner_can_list_and_revoke_invites(ws_client, owner_h):
    jid = _create_job(ws_client, owner_h, "invite-mgmt-kb")
    inv = _create_invite(ws_client, owner_h, jid, "viewer")

    listing = ws_client.get(f"/api/jobs/{jid}/invites", headers=owner_h)
    assert listing.status_code == 200, listing.text
    invite_ids = [i["invite_id"] for i in listing.json()["invites"]]
    assert inv["invite_id"] in invite_ids

    revoked = ws_client.delete(f"/api/jobs/{jid}/invites/{inv['invite_id']}", headers=owner_h)
    assert revoked.status_code == 200, revoked.text

    rejoin = ws_client.post(f"/api/jobs/join/{inv['token']}", headers=owner_h)
    assert rejoin.status_code == 404, rejoin.text


def test_owner_removes_member_revokes_access(ws_client, owner_h, member_h):
    jid = _create_job(ws_client, owner_h, "revoke-kb")
    inv = _create_invite(ws_client, owner_h, jid, "viewer")
    ws_client.post(f"/api/jobs/join/{inv['token']}", headers=member_h)

    members = ws_client.get(f"/api/jobs/{jid}/members", headers=owner_h).json()
    roles_by_email = {m["email"]: m["role"] for m in members}
    assert roles_by_email.get("ws-owner@test.local") == "owner"
    assert roles_by_email.get("ws-member@test.local") == "viewer"
    member_user_id = next(m["user_id"] for m in members if m["role"] == "viewer")

    q_before = ws_client.get(f"/api/jobs/{jid}/query",
                             params={"question": "anything", "n_sources": 1}, headers=member_h)
    assert q_before.status_code == 200, q_before.text

    removed = ws_client.delete(f"/api/jobs/{jid}/members/{member_user_id}", headers=owner_h)
    assert removed.status_code == 200, removed.text

    q_after = ws_client.get(f"/api/jobs/{jid}/query",
                            params={"question": "anything", "n_sources": 1}, headers=member_h)
    assert q_after.status_code == 403, q_after.text


def test_owner_can_change_member_role(ws_client, owner_h, member_h):
    jid = _create_job(ws_client, owner_h, "reroleable-kb")
    inv = _create_invite(ws_client, owner_h, jid, "viewer")
    ws_client.post(f"/api/jobs/join/{inv['token']}", headers=member_h)

    from literature_rag.database import get_db_session, UserCRUD
    db = get_db_session()
    member_user_id = UserCRUD.get_by_email(db, "ws-member@test.local").id

    up_before = ws_client.post(f"/api/jobs/{jid}/upload/async", headers=member_h,
                               files={"file": ("t.pdf", b"%PDF-1.4 x", "application/pdf")},
                               data={"phase": "P1", "topic": "T"})
    assert up_before.status_code == 403, up_before.text

    changed = ws_client.patch(f"/api/jobs/{jid}/members/{member_user_id}",
                              json={"role": "editor"}, headers=owner_h)
    assert changed.status_code == 200, changed.text
    assert changed.json()["role"] == "editor"

    with patch("literature_rag.job_tasks._ingest_pdf_to_job",
               return_value={"success": True, "doc_id": "d4", "chunks_indexed": 1}):
        up_after = ws_client.post(f"/api/jobs/{jid}/upload/async", headers=member_h,
                                  files={"file": ("t.pdf", b"%PDF-1.4 x", "application/pdf")},
                                  data={"phase": "P1", "topic": "T"})
    assert up_after.status_code == 200, up_after.text


def test_invalid_token_join_returns_404(ws_client, stranger_h):
    r = ws_client.post("/api/jobs/join/not-a-real-token", headers=stranger_h)
    assert r.status_code == 404, r.text


def test_owner_cannot_remove_self_and_invite_requires_valid_role(ws_client, owner_h, owner_user_id):
    jid = _create_job(ws_client, owner_h, "solo-kb")

    bad = ws_client.post(f"/api/jobs/{jid}/invites", json={"role": "owner"}, headers=owner_h)
    assert bad.status_code == 400, bad.text

    remove_self = ws_client.delete(f"/api/jobs/{jid}/members/{owner_user_id}", headers=owner_h)
    assert remove_self.status_code == 400, remove_self.text


def test_non_owner_cannot_manage_invites_or_members(ws_client, owner_h, member_h):
    jid = _create_job(ws_client, owner_h, "editor-cant-manage-kb")
    inv = _create_invite(ws_client, owner_h, jid, "editor")
    ws_client.post(f"/api/jobs/join/{inv['token']}", headers=member_h)

    from literature_rag.database import get_db_session, UserCRUD
    db = get_db_session()
    member_user_id = UserCRUD.get_by_email(db, "ws-member@test.local").id

    forbidden_invite = ws_client.post(f"/api/jobs/{jid}/invites", json={"role": "viewer"}, headers=member_h)
    assert forbidden_invite.status_code == 403, forbidden_invite.text

    forbidden_remove = ws_client.delete(f"/api/jobs/{jid}/members/{member_user_id}", headers=member_h)
    assert forbidden_remove.status_code == 403, forbidden_remove.text
