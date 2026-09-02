"""process_job_upload updates UploadTaskRecord through the lifecycle."""
from unittest.mock import patch


def test_process_job_upload_marks_completed(tmp_path):
    from literature_rag.database import init_db, get_db_session, UserCRUD, JobCRUD, UploadTaskCRUD
    from literature_rag import job_tasks

    init_db()
    db = get_db_session()
    user = UserCRUD.create(db, email="qtask@test.local", password_hash="x")
    job = JobCRUD.create(db, user_id=user.id, name="q-job")
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 fake")
    UploadTaskCRUD.create(db, task_id="t1", filename="doc.pdf", phase="P1",
                          topic="T", status="queued", temp_file_path=str(f))

    with patch.object(job_tasks, "_ingest_pdf_to_job",
                      return_value={"success": True, "doc_id": "d1", "chunks_indexed": 3}):
        out = job_tasks.process_job_upload("t1", job.id, str(f), "P1", "T", "doc.pdf")

    assert out["success"] is True
    rec = UploadTaskCRUD.get_by_task_id(get_db_session(), "t1")
    assert rec.status == "completed" and rec.progress == 100
    assert not f.exists()  # temp cleaned


def test_process_job_upload_marks_failed(tmp_path):
    from literature_rag.database import init_db, get_db_session, UserCRUD, JobCRUD, UploadTaskCRUD
    from literature_rag import job_tasks

    init_db()
    db = get_db_session()
    user = UserCRUD.create(db, email="qtask2@test.local", password_hash="x")
    job = JobCRUD.create(db, user_id=user.id, name="q-job2")
    f = tmp_path / "bad.pdf"
    f.write_bytes(b"nope")
    UploadTaskCRUD.create(db, task_id="t2", filename="bad.pdf", phase="P1",
                          topic="T", status="queued", temp_file_path=str(f))

    with patch.object(job_tasks, "_ingest_pdf_to_job", side_effect=RuntimeError("boom")):
        out = job_tasks.process_job_upload("t2", job.id, str(f), "P1", "T", "bad.pdf")

    assert out["success"] is False
    rec = UploadTaskCRUD.get_by_task_id(get_db_session(), "t2")
    assert rec.status == "failed" and "boom" in (rec.error or "")
    assert not f.exists()
