"""Public workspaces: anonymous + unrelated-user read access to is_public jobs.

Follows tests/test_workspace_access.py's TestClient patterns. Owners/jobs are
created directly against the DB (JobCRUD) rather than through the API, since
these tests don't need a real owner session - only an unrelated logged-in
user (registered once, module-scoped) and anonymous (no auth header) calls.
"""
import uuid

import pytest
from fastapi.testclient import TestClient


def _register(client, email):
    r = client.post("/api/auth/register", json={
        "email": email, "password": "Passw0rd!x", "name": email.split("@")[0]})
    tok = (r.json().get("access_token")
           or client.post("/api/auth/login", json={
               "email": email, "password": "Passw0rd!x"}).json()["access_token"])
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def pw_client():
    from literature_rag.api import app
    return TestClient(app)


@pytest.fixture(scope="module")
def stranger_h(pw_client):
    return _register(pw_client, "pw-stranger@test.local")


def _make_job(is_public: bool, name: str):
    """Create an owner + job directly in the DB, bypassing the API/auth.

    Returns (owner_id, owner_email, job_id) rather than the live ORM
    instances - the DB session used here is closed by the time callers
    inspect the result, so lazy attribute access on a detached instance
    would raise DetachedInstanceError.
    """
    from literature_rag.database import get_db_session, UserCRUD, JobCRUD
    db = get_db_session()
    uid = uuid.uuid4().hex[:10]
    owner = UserCRUD.create(db, email=f"pw-owner-{uid}@t.local", password_hash="x")
    owner_id, owner_email = owner.id, owner.email
    job = JobCRUD.create(db, user_id=owner.id, name=name)
    job.is_public = is_public
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()
    return owner_id, owner_email, job_id


# ============================================================================
# Anonymous access (no Authorization header at all)
# ============================================================================

def test_anonymous_lists_public_job_with_viewer_role(pw_client):
    _, _, job_id = _make_job(True, "pub-list-kb")

    listing = pw_client.get("/api/jobs")
    assert listing.status_code == 200, listing.text
    matches = [j for j in listing.json()["jobs"] if j["id"] == job_id]
    assert len(matches) == 1
    assert matches[0]["role"] == "viewer"
    assert matches[0]["is_public"] is True


def test_anonymous_does_not_see_private_job(pw_client):
    _, _, job_id = _make_job(False, "priv-list-kb")

    listing = pw_client.get("/api/jobs")
    assert listing.status_code == 200, listing.text
    matches = [j for j in listing.json()["jobs"] if j["id"] == job_id]
    assert len(matches) == 0


def test_anonymous_can_query_public_job(pw_client):
    _, _, job_id = _make_job(True, "pub-query-kb")

    q = pw_client.get(f"/api/jobs/{job_id}/query",
                      params={"question": "anything", "n_sources": 1})
    assert q.status_code == 200, q.text


def test_anonymous_can_chat_public_job_or_gets_llm_unavailable(pw_client):
    # /chat requires GROQ_API_KEY to be configured; in the test environment
    # it may be unset, in which case the route correctly 503s *after* the
    # membership/auth check has already passed. Either way, it must not be
    # 401/403 - that's the behavior under test here.
    _, _, job_id = _make_job(True, "pub-chat-kb")

    r = pw_client.get(f"/api/jobs/{job_id}/chat",
                      params={"question": "anything", "n_sources": 1})
    assert r.status_code not in (401, 403), r.text


def test_anonymous_upload_and_delete_forbidden_on_public_job(pw_client):
    _, _, job_id = _make_job(True, "pub-write-kb")

    up = pw_client.post(f"/api/jobs/{job_id}/upload/async",
                        files={"file": ("t.pdf", b"%PDF-1.4 x", "application/pdf")},
                        data={"phase": "P1", "topic": "T"})
    assert up.status_code in (401, 403), up.text

    deleted = pw_client.delete(f"/api/jobs/{job_id}")
    assert deleted.status_code in (401, 403), deleted.text


def test_anonymous_query_on_private_job_unauthorized(pw_client):
    _, _, job_id = _make_job(False, "priv-query-kb")

    q = pw_client.get(f"/api/jobs/{job_id}/query",
                      params={"question": "anything", "n_sources": 1})
    assert q.status_code in (401, 403), q.text


def test_anonymous_documents_and_members_readable_on_public_job(pw_client):
    _, owner_email, job_id = _make_job(True, "pub-docs-kb")

    docs = pw_client.get(f"/api/jobs/{job_id}/documents")
    assert docs.status_code == 200, docs.text

    members = pw_client.get(f"/api/jobs/{job_id}/members")
    assert members.status_code == 200, members.text
    roles = {m["email"]: m["role"] for m in members.json()}
    assert roles.get(owner_email) == "owner"


def test_anonymous_documents_forbidden_on_private_job(pw_client):
    _, _, job_id = _make_job(False, "priv-docs-kb")

    docs = pw_client.get(f"/api/jobs/{job_id}/documents")
    assert docs.status_code in (401, 403), docs.text


# ============================================================================
# Unrelated logged-in user (registered, not owner/member of the job)
# ============================================================================

def test_unrelated_user_lists_and_queries_public_job(pw_client, stranger_h):
    _, _, job_id = _make_job(True, "pub-stranger-kb")

    listing = pw_client.get("/api/jobs", headers=stranger_h)
    assert listing.status_code == 200, listing.text
    matches = [j for j in listing.json()["jobs"] if j["id"] == job_id]
    assert len(matches) == 1
    assert matches[0]["role"] == "viewer"

    q = pw_client.get(f"/api/jobs/{job_id}/query",
                      params={"question": "anything", "n_sources": 1}, headers=stranger_h)
    assert q.status_code == 200, q.text


def test_unrelated_user_write_forbidden_on_public_job(pw_client, stranger_h):
    _, _, job_id = _make_job(True, "pub-stranger-write-kb")

    up = pw_client.post(f"/api/jobs/{job_id}/upload/async", headers=stranger_h,
                        files={"file": ("t.pdf", b"%PDF-1.4 x", "application/pdf")},
                        data={"phase": "P1", "topic": "T"})
    assert up.status_code == 403, up.text

    deleted = pw_client.delete(f"/api/jobs/{job_id}", headers=stranger_h)
    assert deleted.status_code == 403, deleted.text


def test_unrelated_user_forbidden_on_private_job(pw_client, stranger_h):
    _, _, job_id = _make_job(False, "priv-stranger-kb")

    q = pw_client.get(f"/api/jobs/{job_id}/query",
                      params={"question": "anything", "n_sources": 1}, headers=stranger_h)
    assert q.status_code == 403, q.text


# ============================================================================
# Owner toggling is_public via PATCH
# ============================================================================

def test_owner_can_toggle_is_public_via_patch(pw_client):
    from literature_rag.auth import create_access_token

    owner_id, owner_email, job_id = _make_job(False, "toggle-kb")
    token = create_access_token(owner_id, owner_email)
    headers = {"Authorization": f"Bearer {token}"}

    # Anonymous cannot query yet (still private)
    q_before = pw_client.get(f"/api/jobs/{job_id}/query",
                             params={"question": "anything", "n_sources": 1})
    assert q_before.status_code in (401, 403), q_before.text

    patched = pw_client.patch(f"/api/jobs/{job_id}", params={"is_public": True}, headers=headers)
    assert patched.status_code == 200, patched.text
    assert patched.json()["is_public"] is True

    q_after = pw_client.get(f"/api/jobs/{job_id}/query",
                            params={"question": "anything", "n_sources": 1})
    assert q_after.status_code == 200, q_after.text
