"""Data source configuration router."""

import json
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db, DataSourceConnectionCRUD
from ..models import (
    DataSourceConnectionInfo,
    DataSourceConnectionListResponse,
    DataSourceConnectionUpsertRequest
)

router = APIRouter(prefix="/api/settings", tags=["DataSources"])

ALLOWED_PROVIDERS = {
    "google_drive",
    "onedrive",
    "notion",
    "github",
    "confluence",
}


def _validate_provider(provider: str):
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported provider"
        )


@router.get("/data-sources", response_model=DataSourceConnectionListResponse)
async def list_data_sources(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    connections = DataSourceConnectionCRUD.list_for_user(db, current_user.id)
    payload = []
    for conn in connections:
        try:
            config = json.loads(conn.config_json or "{}")
        except Exception:
            config = {}
        payload.append(
            DataSourceConnectionInfo(
                provider=conn.provider,
                status=conn.status,
                config=config
            )
        )
    return {"connections": payload}


@router.post("/data-sources/{provider}", response_model=DataSourceConnectionInfo)
async def upsert_data_source(
    provider: str,
    request: DataSourceConnectionUpsertRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_provider(provider)
    config_json = json.dumps(request.config or {})
    conn = DataSourceConnectionCRUD.upsert(
        db=db,
        user_id=current_user.id,
        provider=provider,
        config_json=config_json,
        status=request.status or "configured"
    )
    return DataSourceConnectionInfo(
        provider=conn.provider,
        status=conn.status,
        config=request.config or {}
    )


@router.delete("/data-sources/{provider}")
async def delete_data_source(
    provider: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_provider(provider)
    DataSourceConnectionCRUD.delete(db, current_user.id, provider)
    return {"success": True}
