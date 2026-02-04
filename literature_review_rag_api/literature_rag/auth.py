"""Authentication Module for Literature RAG

Provides JWT token management, password hashing, and OAuth utilities.
"""

import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db, User, UserCRUD, RefreshTokenCRUD

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# JWT Configuration
# Persist a stable secret key so tokens survive server restarts.
# Priority: env var > file-based key > generate-and-save
def _get_or_create_secret_key() -> str:
    """Return a stable JWT secret key that persists across restarts."""
    env_key = os.getenv("JWT_SECRET_KEY")
    if env_key:
        return env_key

    key_file = os.path.join(os.path.dirname(__file__), "..", ".jwt_secret")
    key_file = os.path.abspath(key_file)

    if os.path.exists(key_file):
        with open(key_file, "r") as f:
            return f.read().strip()

    # First run — generate and persist
    new_key = secrets.token_urlsafe(32)
    try:
        with open(key_file, "w") as f:
            f.write(new_key)
        os.chmod(key_file, 0o600)  # Owner-only read/write
        logger.info("Generated and saved new JWT secret key")
    except OSError as e:
        logger.warning(f"Could not persist JWT secret key to file: {e}")
    return new_key

SECRET_KEY = _get_or_create_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

# OAuth redirect URLs
OAUTH_REDIRECT_URL = os.getenv("OAUTH_REDIRECT_URL", "http://localhost:5173/auth/callback")

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# ============================================================================
# JWT UTILITIES
# ============================================================================

def create_access_token(
    user_id: int,
    email: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow()
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, datetime]:
    """
    Create a refresh token.

    Returns:
        Tuple of (token_string, expiration_datetime)
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # Generate a random token
    token = secrets.token_urlsafe(64)

    to_encode = {
        "sub": str(user_id),
        "token": token,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow()
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Returns:
        Token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.debug(f"Token decode error: {e}")
        return None


def hash_token(token: str) -> str:
    """Create a hash of a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# ============================================================================
# TOKEN PAIR GENERATION
# ============================================================================

def create_token_pair(
    user_id: int,
    email: str,
    db: Session,
    device_info: Optional[str] = None,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create both access and refresh tokens.

    Returns:
        Dictionary with access_token, refresh_token, and metadata
    """
    # Create access token
    access_token = create_access_token(user_id, email)

    # Create refresh token
    refresh_token, refresh_expires = create_refresh_token(user_id)

    # Store refresh token hash in database
    RefreshTokenCRUD.create(
        db=db,
        user_id=user_id,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_expires,
        device_info=device_info,
        ip_address=ip_address
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    }


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = UserCRUD.get_by_id(db, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    FastAPI dependency to optionally get the current user.
    Returns None if not authenticated (doesn't raise exception).
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# ============================================================================
# OAUTH UTILITIES
# ============================================================================

async def get_google_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """Fetch user info from Google using access token."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Google API error: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error fetching Google user info: {e}")
        return None


async def get_github_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """Fetch user info from GitHub using access token."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            # Get user info
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )

            if response.status_code != 200:
                logger.error(f"GitHub API error: {response.status_code}")
                return None

            user_data = response.json()

            # Get primary email if not public
            if not user_data.get("email"):
                email_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )

                if email_response.status_code == 200:
                    emails = email_response.json()
                    primary_email = next(
                        (e["email"] for e in emails if e.get("primary")),
                        emails[0]["email"] if emails else None
                    )
                    user_data["email"] = primary_email

            return user_data
    except Exception as e:
        logger.error(f"Error fetching GitHub user info: {e}")
        return None


async def exchange_google_code(code: str, redirect_uri: str) -> Optional[str]:
    """Exchange Google authorization code for access token."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            else:
                logger.error(f"Google token exchange error: {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error exchanging Google code: {e}")
        return None


async def exchange_github_code(code: str) -> Optional[str]:
    """Exchange GitHub authorization code for access token."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            else:
                logger.error(f"GitHub token exchange error: {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error exchanging GitHub code: {e}")
        return None


def get_google_auth_url(state: str, redirect_uri: str) -> str:
    """Generate Google OAuth authorization URL."""
    from urllib.parse import urlencode

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def get_github_auth_url(state: str) -> str:
    """Generate GitHub OAuth authorization URL."""
    from urllib.parse import urlencode

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "scope": "user:email",
        "state": state
    }

    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"
