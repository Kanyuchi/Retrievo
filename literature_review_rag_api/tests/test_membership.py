"""Membership model, invite lifecycle, and role helper."""
import pytest
from fastapi import HTTPException


@pytest.fixture()
def setup():
    from literature_rag.database import init_db, get_db_session, UserCRUD, JobCRUD
    init_db()
    db = get_db_session()
    owner = UserCRUD.create(db, email=f"own-{id(db)}@t.local", password_hash="x")
    other = UserCRUD.create(db, email=f"oth-{id(db)}@t.local", password_hash="x")
    job = JobCRUD.create(db, user_id=owner.id, name="m-kb")
    return db, owner, other, job


def test_owner_is_implicit(setup):
    db, owner, other, job = setup
    from literature_rag.membership import get_job_role, require_job_role
    assert get_job_role(db, job, owner.id) == "owner"
    assert get_job_role(db, job, other.id) is None
    assert require_job_role(db, job, owner.id, "owner") == "owner"
    with pytest.raises(HTTPException):
        require_job_role(db, job, other.id, "viewer")


def test_member_roles_and_order(setup):
    db, owner, other, job = setup
    from literature_rag.database import JobMemberCRUD
    from literature_rag.membership import require_job_role
    JobMemberCRUD.add(db, job.id, other.id, role="viewer")
    assert require_job_role(db, job, other.id, "viewer") == "viewer"
    with pytest.raises(HTTPException):
        require_job_role(db, job, other.id, "editor")
    JobMemberCRUD.set_role(db, job.id, other.id, "editor")
    assert require_job_role(db, job, other.id, "editor") == "editor"
    with pytest.raises(HTTPException):
        require_job_role(db, job, other.id, "owner")
    assert JobMemberCRUD.remove(db, job.id, other.id)
    with pytest.raises(HTTPException):
        require_job_role(db, job, other.id, "viewer")


def test_invite_lifecycle(setup):
    db, owner, other, job = setup
    from literature_rag.database import JobInviteCRUD
    inv = JobInviteCRUD.create(db, job.id, owner.id, role="editor",
                               expires_days=14, max_uses=2)
    assert len(inv.token) > 20
    got = JobInviteCRUD.get_valid_by_token(db, inv.token)
    assert got and got.role == "editor"
    JobInviteCRUD.consume(db, got)
    JobInviteCRUD.consume(db, got)
    assert JobInviteCRUD.get_valid_by_token(db, inv.token) is None  # max uses hit


def test_invite_expiry(setup):
    db, owner, other, job = setup
    from datetime import datetime, timedelta
    from literature_rag.database import JobInviteCRUD
    inv = JobInviteCRUD.create(db, job.id, owner.id, expires_days=1)
    inv.expires_at = datetime.utcnow() - timedelta(hours=1)
    db.commit()
    assert JobInviteCRUD.get_valid_by_token(db, inv.token) is None
