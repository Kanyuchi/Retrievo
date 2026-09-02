"""Workspace role checks.

Role order: viewer < editor < owner. The job's owner (job.user_id) has
implicit "owner" role; everyone else needs a JobMember row.
"""
from fastapi import HTTPException, status

ROLE_ORDER = {"viewer": 1, "editor": 2, "owner": 3}


def get_job_role(db, job, user_id: int):
    """Return the user's role in this job, or None."""
    if job.user_id == user_id:
        return "owner"
    from .database import JobMemberCRUD
    return JobMemberCRUD.get_role(db, job.id, user_id)


def require_job_role(db, job, user_id: int, min_role: str = "viewer"):
    """Raise 403 unless the user holds at least min_role in the job."""
    role = get_job_role(db, job, user_id)
    if role is None or ROLE_ORDER.get(role, 0) < ROLE_ORDER[min_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    return role
