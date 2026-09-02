"""Plan-tier quotas are enforced on KB creation, uploads, and queries."""
from unittest.mock import patch
from fastapi.testclient import TestClient


def _client_and_token(email):
    from literature_rag.api import app
    client = TestClient(app)
    r = client.post("/api/auth/register", json={
        "email": email, "password": "Passw0rd!x", "name": "Q"})
    tok = (r.json().get("access_token")
           or client.post("/api/auth/login", json={
               "email": email, "password": "Passw0rd!x"}).json()["access_token"])
    return client, {"Authorization": f"Bearer {tok}"}


def test_free_tier_kb_creation_limit():
    client, h = _client_and_token("quota-kb@test.local")
    for i in range(3):
        r = client.post("/api/jobs", json={"name": f"kb-{i}"}, headers=h)
        assert r.status_code == 200, r.text
    r = client.post("/api/jobs", json={"name": "kb-overflow"}, headers=h)
    assert r.status_code == 403
    body = str(r.json()).lower()
    assert "knowledge base" in body or "limit" in body or "denied" in body


def test_enterprise_tier_bypasses_kb_limit():
    client, h = _client_and_token("quota-ent@test.local")
    from literature_rag.database import get_db_session, UserCRUD
    db = get_db_session()
    user = UserCRUD.get_by_email(db, "quota-ent@test.local")
    user.plan_tier = "enterprise"
    db.commit()
    for i in range(4):
        r = client.post("/api/jobs", json={"name": f"ent-kb-{i}"}, headers=h)
        assert r.status_code == 200, r.text


def test_upload_rejected_over_tier_file_size(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    client, h = _client_and_token("quota-up@test.local")
    jid = client.post("/api/jobs", json={"name": "up-kb"}, headers=h).json()["id"]

    from literature_rag.quotas import QUOTA_LIMITS, PlanTier
    original = QUOTA_LIMITS[PlanTier.FREE].max_file_size_bytes
    QUOTA_LIMITS[PlanTier.FREE].max_file_size_bytes = 10  # 10 bytes
    try:
        r = client.post(f"/api/jobs/{jid}/upload/async", headers=h,
                        files={"file": ("t.pdf", b"%PDF-1.4 bigger than ten bytes", "application/pdf")},
                        data={"phase": "P1", "topic": "T"})
        assert r.status_code == 403, r.text
    finally:
        QUOTA_LIMITS[PlanTier.FREE].max_file_size_bytes = original


def test_query_rejected_when_daily_api_calls_exhausted():
    from datetime import datetime
    client, h = _client_and_token("quota-api@test.local")
    jid = client.post("/api/jobs", json={"name": "api-kb"}, headers=h).json()["id"]

    from literature_rag.database import get_db_session, UserCRUD
    from literature_rag.quotas import QUOTA_LIMITS, PlanTier
    db = get_db_session()
    user = UserCRUD.get_by_email(db, "quota-api@test.local")
    user.api_calls_today = QUOTA_LIMITS[PlanTier.FREE].max_api_calls_per_day
    user.last_api_call_date = datetime.utcnow()
    db.commit()

    r = client.get(f"/api/jobs/{jid}/query",
                   params={"question": "anything", "n_sources": 1}, headers=h)
    assert r.status_code == 429, r.text
