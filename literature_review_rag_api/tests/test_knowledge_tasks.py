"""process_insights_build / process_graph_build update UploadTaskRecord through
the lifecycle, mirroring tests/test_job_tasks.py for the upload queue task."""
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


def test_process_insights_build_marks_completed():
    from literature_rag.database import init_db, get_db_session, UserCRUD, JobCRUD, UploadTaskCRUD
    from literature_rag import knowledge_tasks

    init_db()
    db = get_db_session()
    user = UserCRUD.create(db, email="ktask1@test.local", password_hash="x")
    job = JobCRUD.create(db, user_id=user.id, name="k-job1")
    UploadTaskCRUD.create(db, task_id="kt1", filename="insights-build", phase="-",
                          topic="-", status="queued")

    fake_result = {"documents_processed": 2, "claims_extracted": 5, "gaps_detected": 1}
    with patch.object(knowledge_tasks, "run_insights_for_job", return_value=fake_result):
        out = knowledge_tasks.process_insights_build("kt1", job.id, 50)

    assert out == fake_result
    rec = UploadTaskCRUD.get_by_task_id(get_db_session(), "kt1")
    assert rec.status == "completed" and rec.progress == 100
    assert rec.result_json and "claims_extracted" in rec.result_json


def test_process_insights_build_marks_failed():
    from literature_rag.database import init_db, get_db_session, UserCRUD, JobCRUD, UploadTaskCRUD
    from literature_rag import knowledge_tasks

    init_db()
    db = get_db_session()
    user = UserCRUD.create(db, email="ktask2@test.local", password_hash="x")
    job = JobCRUD.create(db, user_id=user.id, name="k-job2")
    UploadTaskCRUD.create(db, task_id="kt2", filename="insights-build", phase="-",
                          topic="-", status="queued")

    with patch.object(knowledge_tasks, "run_insights_for_job", side_effect=RuntimeError("boom")):
        out = knowledge_tasks.process_insights_build("kt2", job.id, 50)

    assert out.get("success") is False
    rec = UploadTaskCRUD.get_by_task_id(get_db_session(), "kt2")
    assert rec.status == "failed" and "boom" in (rec.error or "")


def test_process_graph_build_marks_completed():
    from literature_rag.database import init_db, get_db_session, UserCRUD, JobCRUD, UploadTaskCRUD
    from literature_rag import knowledge_tasks

    init_db()
    db = get_db_session()
    user = UserCRUD.create(db, email="ktask3@test.local", password_hash="x")
    job = JobCRUD.create(db, user_id=user.id, name="k-job3")
    UploadTaskCRUD.create(db, task_id="kt3", filename="graph-build", phase="-",
                          topic="-", status="queued")

    fake_result = {"claims_processed": 4, "entities_created": 6, "edges_created": 3}
    with patch.object(knowledge_tasks, "run_graph_build_for_job", return_value=fake_result):
        out = knowledge_tasks.process_graph_build("kt3", job.id, 400)

    assert out == fake_result
    rec = UploadTaskCRUD.get_by_task_id(get_db_session(), "kt3")
    assert rec.status == "completed" and rec.progress == 100
    assert rec.result_json and "entities_created" in rec.result_json


def test_process_graph_build_marks_failed():
    from literature_rag.database import init_db, get_db_session, UserCRUD, JobCRUD, UploadTaskCRUD
    from literature_rag import knowledge_tasks

    init_db()
    db = get_db_session()
    user = UserCRUD.create(db, email="ktask4@test.local", password_hash="x")
    job = JobCRUD.create(db, user_id=user.id, name="k-job4")
    UploadTaskCRUD.create(db, task_id="kt4", filename="graph-build", phase="-",
                          topic="-", status="queued")

    with patch.object(knowledge_tasks, "run_graph_build_for_job", side_effect=RuntimeError("kapow")):
        out = knowledge_tasks.process_graph_build("kt4", job.id, 400)

    assert out.get("success") is False
    rec = UploadTaskCRUD.get_by_task_id(get_db_session(), "kt4")
    assert rec.status == "failed" and "kapow" in (rec.error or "")


def test_insights_run_async_returns_task_id_and_status_route_answers():
    from literature_rag import knowledge_tasks

    client, h = _client_and_token("ktask-http@test.local")
    jid = client.post("/api/jobs", json={"name": "async-insights-kb"}, headers=h).json()["id"]

    fake_result = {"documents_processed": 0, "claims_extracted": 0, "gaps_detected": 0}
    with patch.object(knowledge_tasks, "run_insights_for_job", return_value=fake_result):
        r = client.post(f"/api/jobs/{jid}/insights/run/async",
                        params={"doc_limit": 10}, headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "task_id" in body and body.get("status_url", "").endswith(body["task_id"] + "/status")

        status_r = client.get(body["status_url"], headers=h)
        assert status_r.status_code == 200, status_r.text
        status_body = status_r.json()
        assert status_body["task_id"] == body["task_id"]
        assert status_body["status"] in ("queued", "processing", "completed")


def test_graph_build_async_returns_task_id_and_status_route_answers():
    from literature_rag import knowledge_tasks

    client, h = _client_and_token("ktask-http2@test.local")
    jid = client.post("/api/jobs", json={"name": "async-graph-kb"}, headers=h).json()["id"]

    fake_result = {"claims_processed": 0, "entities_created": 0, "edges_created": 0}
    with patch.object(knowledge_tasks, "run_graph_build_for_job", return_value=fake_result):
        r = client.post(f"/api/jobs/{jid}/graph/build/async", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "task_id" in body and body.get("status_url", "").endswith(body["task_id"] + "/status")

        status_r = client.get(body["status_url"], headers=h)
        assert status_r.status_code == 200, status_r.text
        assert status_r.json()["task_id"] == body["task_id"]
