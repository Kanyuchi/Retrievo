"""GDPR-grade purge helpers.

purge_job removes every trace of a knowledge base; purge_user removes every
trace of an account. External stores (vectors, object storage, BM25 pickles)
are deleted best-effort with logged failures; database rows are deleted in
FK-safe order and committed by the caller's session.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def purge_job(db, job) -> None:
    """Hard-delete a job and everything scoped to it."""
    from .config import load_config
    from .database import (
        ChatMessage, ChatSession, Document, DocumentRelation, JobInvite,
        JobMember, KnowledgeClaim, KnowledgeCluster, KnowledgeEdge,
        KnowledgeEntity, KnowledgeEntityOccurrence, KnowledgeGap,
    )
    from .storage import get_storage_auto

    cfg = load_config()
    job_id = job.id

    # --- external stores (best effort) ---
    try:
        from .routers.jobs import get_job_collection
        client, _ = get_job_collection(job)
        client.delete_collection(job.collection_name)
    except Exception as e:
        logger.warning(f"purge_job {job_id}: vector collection delete failed: {e}")

    try:
        bm25_path = Path(cfg.storage.indices_path) / f"bm25_job_{job_id}.pkl"
        if bm25_path.exists():
            bm25_path.unlink()
    except Exception as e:
        logger.warning(f"purge_job {job_id}: bm25 delete failed: {e}")

    try:
        storage = get_storage_auto()
        for doc in db.query(Document).filter(Document.job_id == job_id).all():
            if doc.storage_key:
                try:
                    storage.delete_pdf(doc.storage_key)
                except Exception as e:
                    logger.warning(f"purge_job {job_id}: storage delete {doc.storage_key}: {e}")
    except Exception as e:
        logger.warning(f"purge_job {job_id}: storage cleanup failed: {e}")

    # --- database rows, FK-safe order ---
    session_ids = [r[0] for r in db.query(ChatSession.id).filter(ChatSession.job_id == job_id).all()]
    if session_ids:
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(ChatSession).filter(ChatSession.id.in_(session_ids)).delete(synchronize_session=False)

    db.query(KnowledgeGap).filter(KnowledgeGap.job_id == job_id).delete(synchronize_session=False)
    db.query(KnowledgeEntityOccurrence).filter(KnowledgeEntityOccurrence.job_id == job_id).delete(synchronize_session=False)
    db.query(KnowledgeEdge).filter(KnowledgeEdge.job_id == job_id).delete(synchronize_session=False)
    db.query(KnowledgeClaim).filter(KnowledgeClaim.job_id == job_id).delete(synchronize_session=False)
    db.query(KnowledgeEntity).filter(KnowledgeEntity.job_id == job_id).delete(synchronize_session=False)
    db.query(KnowledgeCluster).filter(KnowledgeCluster.job_id == job_id).delete(synchronize_session=False)
    db.query(DocumentRelation).filter(DocumentRelation.job_id == job_id).delete(synchronize_session=False)
    db.query(JobMember).filter(JobMember.job_id == job_id).delete(synchronize_session=False)
    db.query(JobInvite).filter(JobInvite.job_id == job_id).delete(synchronize_session=False)
    db.query(Document).filter(Document.job_id == job_id).delete(synchronize_session=False)

    db.delete(job)
    db.commit()
    logger.info(f"purge_job {job_id}: complete")


def purge_user(db, user) -> None:
    """Hard-delete an account: their jobs, their traces in others' jobs, the user."""
    from .database import (
        ChatMessage, ChatSession, DataSourceConnection, Job, JobInvite,
        JobMember, RefreshToken,
    )

    user_id = user.id

    for job in db.query(Job).filter(Job.user_id == user_id).all():
        purge_job(db, job)

    # Their chat sessions in OTHER people's jobs
    session_ids = [r[0] for r in db.query(ChatSession.id).filter(ChatSession.user_id == user_id).all()]
    if session_ids:
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(ChatSession).filter(ChatSession.id.in_(session_ids)).delete(synchronize_session=False)

    db.query(JobMember).filter(JobMember.user_id == user_id).delete(synchronize_session=False)
    db.query(JobInvite).filter(JobInvite.created_by == user_id).delete(synchronize_session=False)
    db.query(DataSourceConnection).filter(DataSourceConnection.user_id == user_id).delete(synchronize_session=False)
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete(synchronize_session=False)

    db.delete(user)
    db.commit()
    logger.info(f"purge_user {user_id}: complete")
