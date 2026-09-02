"""Async job upload enqueues (or inlines) and is pollable via status route."""
from unittest.mock import patch
from fastapi.testclient import TestClient


def test_async_upload_returns_task_and_status(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    from literature_rag.api import app
    client = TestClient(app)
    r = client.post("/api/auth/register", json={
        "email": "async@test.local", "password": "Passw0rd!x", "name": "A"})
    tok = (r.json().get("access_token")
           or client.post("/api/auth/login", json={
               "email": "async@test.local", "password": "Passw0rd!x"}).json()["access_token"])
    h = {"Authorization": f"Bearer {tok}"}
    jid = client.post("/api/jobs", json={"name": "async-kb"}, headers=h).json()["id"]

    with patch("literature_rag.job_tasks._ingest_pdf_to_job",
               return_value={"success": True, "doc_id": "d", "chunks_indexed": 1}):
        r = client.post(f"/api/jobs/{jid}/upload/async", headers=h,
                        files={"file": ("t.pdf", b"%PDF-1.4 x", "application/pdf")},
                        data={"phase": "P1", "topic": "T"})
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]
    s = client.get(f"/api/upload/{task_id}/status", headers=h)
    assert s.status_code == 200
    assert s.json().get("status") in ("queued", "processing", "completed")
