"""Workspace role checks.

Role order: viewer < editor < owner. The job's owner (job.user_id) has
implicit "owner" role; everyone else needs a JobMember row. Public
workspaces (job.is_public) grant an implicit "viewer" role to anyone,
including anonymous callers (user_id=None), who has no stronger explicit
role.
"""
from typing import Optional

from fastapi import HTTPException, status

ROLE_ORDER = {"viewer": 1, "editor": 2, "owner": 3}


def get_job_role(db, job, user_id: Optional[int]):
    """Return the user's role in this job, or None.

    user_id may be None for anonymous callers - anonymous users can never
    be the owner or an explicit member, but may still get "viewer" via
    job.is_public below.
    """
    if user_id is not None and job.user_id == user_id:
        return "owner"

    if user_id is not None:
        from .database import JobMemberCRUD
        role = JobMemberCRUD.get_role(db, job.id, user_id)
        if role is not None:
            return role

    if getattr(job, "is_public", False):
        return "viewer"

    return None


def require_job_role(db, job, user_id: Optional[int], min_role: str = "viewer"):
    """Raise 403 unless the user holds at least min_role in the job.

    For anonymous callers (user_id=None) on a non-public job, raise 401
    instead of 403 - there's no identity to deny access to yet, so the
    correct response is "authenticate first".
    """
    role = get_job_role(db, job, user_id)
    if role is None or ROLE_ORDER.get(role, 0) < ROLE_ORDER[min_role]:
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    return role
