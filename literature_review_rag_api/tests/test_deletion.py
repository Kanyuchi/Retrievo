"""purge_user / purge_job remove every trace, FK-safely."""
import uuid


def _fixture(db):
    from literature_rag.database import (
        UserCRUD, JobCRUD, DocumentCRUD, JobMemberCRUD, JobInviteCRUD,
        KnowledgeClaimCRUD, ChatSessionCRUD, ChatMessageCRUD, DocumentRelationCRUD,
    )
    uid = uuid.uuid4().hex[:10]
    owner = UserCRUD.create(db, email=f"del-o-{uid}@t.local", password_hash="x")
    member = UserCRUD.create(db, email=f"del-m-{uid}@t.local", password_hash="x")
    job = JobCRUD.create(db, user_id=owner.id, name="del-kb")
    DocumentCRUD.create(db, job_id=job.id, doc_id=f"d-{uid}", filename="f.pdf",
                        original_filename="f.pdf")
    JobMemberCRUD.add(db, job.id, member.id, role="editor")
    JobInviteCRUD.create(db, job.id, owner.id)
    KnowledgeClaimCRUD.create(db, job.id, f"d-{uid}", "a claim", 1)
    DocumentRelationCRUD.replace_for_doc(db, job.id, f"d-{uid}", [("other", 0.5)])
    sess = ChatSessionCRUD.create(db, member.id, job.id, title="t")
    ChatMessageCRUD.create(db, sess.id, "user", "hello")
    return owner, member, job


def _counts(db, job_id, user_ids):
    from sqlalchemy import text
    out = {}
    for t, col in [("jobs", "id"), ("documents", "job_id"), ("job_members", "job_id"),
                   ("job_invites", "job_id"), ("knowledge_claims", "job_id"),
                   ("document_relations", "job_id"), ("chat_sessions", "job_id")]:
        out[t] = db.execute(text(f"SELECT count(*) FROM {t} WHERE {col} = :v"),
                            {"v": job_id}).scalar()
    out["users"] = db.execute(
        text("SELECT count(*) FROM users WHERE id IN :ids").bindparams(
            __import__("sqlalchemy").bindparam("ids", expanding=True)),
        {"ids": list(user_ids)}).scalar()
    return out


def test_purge_user_removes_everything():
    from literature_rag.database import init_db, get_db_session
    from literature_rag.deletion import purge_user
    init_db()
    db = get_db_session()
    owner, member, job = _fixture(db)
    jid, oid, mid = job.id, owner.id, member.id

    purge_user(db, owner)

    c = _counts(db, jid, [oid])
    assert all(v == 0 for v in c.values()), c
    # member account survives, just lost the workspace
    from literature_rag.database import UserCRUD
    assert UserCRUD.get_by_id(db, mid) is not None


def test_purge_member_keeps_job():
    from literature_rag.database import init_db, get_db_session, JobCRUD, JobMemberCRUD
    from literature_rag.deletion import purge_user
    init_db()
    db = get_db_session()
    owner, member, job = _fixture(db)
    jid, mid = job.id, member.id

    purge_user(db, member)

    assert JobCRUD.get_by_id(db, jid) is not None            # job intact
    assert JobMemberCRUD.get_role(db, jid, mid) is None      # membership gone
    from sqlalchemy import text
    assert db.execute(text("SELECT count(*) FROM chat_sessions WHERE user_id = :u"),
                      {"u": mid}).scalar() == 0              # their sessions gone


def test_graph_clear_order_is_fk_safe():
    """Occurrences/edges reference entities — clearing must delete them first
    (regression: Postgres FK violation on graph rebuild)."""
    from literature_rag.database import (
        init_db, get_db_session, UserCRUD, JobCRUD,
        KnowledgeEntityCRUD, KnowledgeEdgeCRUD, KnowledgeEntityOccurrenceCRUD,
        KnowledgeClusterCRUD,
    )
    import uuid
    init_db()
    db = get_db_session()
    u = UserCRUD.create(db, email=f"gfk-{uuid.uuid4().hex[:8]}@t.local", password_hash="x")
    job = JobCRUD.create(db, user_id=u.id, name="gfk-kb")
    e1 = KnowledgeEntityCRUD.get_or_create(db, job.id, "EntityA")
    e2 = KnowledgeEntityCRUD.get_or_create(db, job.id, "EntityB")
    KnowledgeEdgeCRUD.create(db, job.id, e1.id, e2.id, "related_to")
    KnowledgeEntityOccurrenceCRUD.create(db, job.id, e1.id, "doc1")

    # Same order as routers/graph.py build_knowledge_graph clear step
    KnowledgeEntityOccurrenceCRUD.delete_for_job(db, job.id)
    KnowledgeEdgeCRUD.delete_for_job(db, job.id)
    KnowledgeEntityCRUD.delete_for_job(db, job.id)
    KnowledgeClusterCRUD.delete_for_job(db, job.id)
    assert KnowledgeEntityCRUD.count_for_job(db, job.id) == 0
