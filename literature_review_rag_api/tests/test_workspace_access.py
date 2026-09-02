"""Team workspace access: role-based checks (Task 2).

Membership is granted directly via JobMemberCRUD here (there's no HTTP
invite endpoint yet at this stage - that's Task 3) so these tests isolate
the route-level require_job_role() enforcement added in Task 2.

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


def _create_job(ws_client, owner_h, name):
    r = ws_client.post("/api/jobs", json={"name": name}, headers=owner_h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _grant_membership(job_id, email, role):
    from literature_rag.database import get_db_session, UserCRUD, JobMemberCRUD
    db = get_db_session()
    user = UserCRUD.get_by_email(db, email)
    JobMemberCRUD.add(db, job_id, user.id, role=role)


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
