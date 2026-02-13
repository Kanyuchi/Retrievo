"""Data source configuration router."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db, DataSourceConnectionCRUD, DataSourceConnection
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

SENSITIVE_KEYS = {
    "client_secret",
    "api_token",
    "integration_token",
    "access_token",
    "refresh_token",
}

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


def _validate_provider(provider: str):
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported provider"
        )


def _load_config(conn) -> Dict[str, Any]:
    try:
        return json.loads(conn.config_json or "{}")
    except Exception:
        return {}


def _save_config(conn, config: Dict[str, Any], db: Session) -> None:
    conn.config_json = json.dumps(config)
    db.commit()
    db.refresh(conn)


def _sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in config.items() if k not in SENSITIVE_KEYS}


def _google_config_for_user(db: Session, user_id: int) -> Dict[str, Any]:
    conn = DataSourceConnectionCRUD.get_for_user_provider(db, user_id, "google_drive")
    if not conn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Drive not configured")
    cfg = _load_config(conn)
    if not cfg.get("client_id") or not cfg.get("client_secret") or not cfg.get("redirect_uri"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Drive credentials incomplete")
    return cfg


def _google_refresh_token(cfg: Dict[str, Any], db: Session, conn) -> str:
    refresh_token = cfg.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Drive refresh token missing")
    payload = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    response = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=20)
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to refresh Google token")
    data = response.json()
    cfg["access_token"] = data.get("access_token")
    cfg["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))).isoformat()
    _save_config(conn, cfg, db)
    return cfg["access_token"]


@router.get("/data-sources", response_model=DataSourceConnectionListResponse)
async def list_data_sources(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    connections = DataSourceConnectionCRUD.list_for_user(db, current_user.id)
    payload = []
    for conn in connections:
        config = _sanitize_config(_load_config(conn))
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
    existing = DataSourceConnectionCRUD.get_for_user_provider(db, current_user.id, provider)
    merged = _load_config(existing) if existing else {}
    for key, value in (request.config or {}).items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        merged[key] = value
    conn = DataSourceConnectionCRUD.upsert(
        db=db,
        user_id=current_user.id,
        provider=provider,
        config_json=json.dumps(merged),
        status=request.status or "configured"
    )
    return DataSourceConnectionInfo(
        provider=conn.provider,
        status=conn.status,
        config=_sanitize_config(merged)
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


@router.get("/data-sources/google_drive/auth-url")
async def google_drive_auth_url(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conn = DataSourceConnectionCRUD.get_for_user_provider(db, current_user.id, "google_drive")
    if not conn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Drive not configured")
    cfg = _load_config(conn)
    if not cfg.get("client_id") or not cfg.get("client_secret") or not cfg.get("redirect_uri"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Drive credentials incomplete")

    state = str(uuid.uuid4())
    cfg["oauth_state"] = state
    _save_config(conn, cfg, db)

    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "include_granted_scopes": "true",
    }
    query = "&".join([f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()])
    return {"url": f"{GOOGLE_AUTH_URL}?{query}"}


@router.get("/data-sources/google_drive/callback")
async def google_drive_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    # Find connection by state
    connections = db.query(DataSourceConnection).filter(
        DataSourceConnection.provider == "google_drive"
    ).all()
    target = None
    cfg_target: Dict[str, Any] = {}
    for conn in connections:
        cfg = _load_config(conn)
        if cfg.get("oauth_state") == state:
            target = conn
            cfg_target = cfg
            break
    if not target or not cfg_target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    payload = {
        "code": code,
        "client_id": cfg_target["client_id"],
        "client_secret": cfg_target["client_secret"],
        "redirect_uri": cfg_target["redirect_uri"],
        "grant_type": "authorization_code",
    }
    response = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=20)
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google token exchange failed")
    data = response.json()
    cfg_target["access_token"] = data.get("access_token")
    cfg_target["refresh_token"] = data.get("refresh_token", cfg_target.get("refresh_token"))
    cfg_target["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))).isoformat()
    cfg_target.pop("oauth_state", None)
    target.config_json = json.dumps(cfg_target)
    target.status = "connected"
    db.commit()

    return RedirectResponse(url="/settings/data-sources?provider=google_drive&connected=1")


@router.get("/data-sources/google_drive/folders")
async def google_drive_folders(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conn = DataSourceConnectionCRUD.get_for_user_provider(db, current_user.id, "google_drive")
    if not conn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Drive not configured")
    cfg = _load_config(conn)
    access_token = cfg.get("access_token")
    expires_at = cfg.get("expires_at")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Drive not connected")
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc) + timedelta(minutes=1):
                access_token = _google_refresh_token(cfg, db, conn)
        except Exception:
            pass

    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "q": "mimeType='application/vnd.google-apps.folder' and trashed=false",
        "fields": "files(id,name)",
        "pageSize": 50,
    }
    resp = requests.get(GOOGLE_DRIVE_FILES_URL, headers=headers, params=params, timeout=20)
    if resp.status_code == 401:
        access_token = _google_refresh_token(cfg, db, conn)
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(GOOGLE_DRIVE_FILES_URL, headers=headers, params=params, timeout=20)
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch Google Drive folders")
    return {"folders": resp.json().get("files", [])}
