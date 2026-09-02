"""Backend switch: VECTOR_BACKEND=pgvector routes to PgVectorStore paths."""
import os
from unittest.mock import patch


def test_default_backend_is_chroma():
    from literature_rag.routers import jobs
    assert jobs.vector_backend() == "chroma"


def test_pgvector_backend_returns_pg_objects():
    from literature_rag.routers import jobs
    from literature_rag.pg_store import PgVectorStore, PgClientShim

    class J:  # minimal Job stand-in
        id = 999
        collection_name = "job_test_backend"
        name = "t"

    with patch.dict(os.environ, {"VECTOR_BACKEND": "pgvector"}):
        with patch.object(jobs, "ensure_pg_schema"):
            client, col = jobs.get_job_collection(J())
            assert isinstance(col, PgVectorStore)
            assert col.name == "job_test_backend"
            assert isinstance(client, PgClientShim)


def test_pgvector_backend_lexical_retriever():
    from literature_rag.routers import jobs
    from literature_rag.pg_store import PgLexicalRetriever
    from literature_rag.database import get_db_session, init_db, JobCRUD, UserCRUD

    init_db()
    db = get_db_session()
    user = UserCRUD.create(db, email="switch@test.local", password_hash="x")
    job = JobCRUD.create(db, user_id=user.id, name="switch-job")
    with patch.dict(os.environ, {"VECTOR_BACKEND": "pgvector"}):
        with patch.object(jobs, "ensure_pg_schema"):
            bm25 = jobs.get_job_bm25_retriever(job.id)
    assert isinstance(bm25, PgLexicalRetriever)
    assert bm25.collection_name == job.collection_name
