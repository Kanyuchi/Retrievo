"""Authentication Router for Literature RAG API

Provides endpoints for user registration, login, token refresh, and OAuth.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from sqlalchemy.orm import Session

from ..database import (
    get_db, init_db, User, UserCRUD, RefreshTokenCRUD, OAuthProvider
)
from ..auth import (
    hash_password, verify_password, create_token_pair,
    decode_token, hash_token, get_current_user,
    get_google_auth_url, get_github_auth_url,
    exchange_google_code, exchange_github_code,
    get_google_user_info, get_github_user_info,
    generate_oauth_state, validate_oauth_state,
    set_auth_cookies, clear_auth_cookies,
    GOOGLE_CLIENT_ID, GITHUB_CLIENT_ID, OAUTH_REDIRECT_URL
)
from ..models import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    UserResponse, OAuthCallbackRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Initialize database on module load
init_db()


# ============================================================================
# REGISTRATION & LOGIN
# ============================================================================

@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Register a new user with email and password.

    Returns access and refresh tokens on successful registration.
    """
    # Check if email already exists
    existing_user = UserCRUD.get_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    password_hash = hash_password(request.password)
    user = UserCRUD.create(
        db=db,
        email=request.email,
        password_hash=password_hash,
        name=request.name
    )

    logger.info(f"New user registered: {user.email}")

    # Generate tokens
    tokens = create_token_pair(user.id, user.email, db)
    set_auth_cookies(response, tokens)
    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.

    Returns access and refresh tokens on successful authentication.
    """
    # Find user
    user = UserCRUD.get_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if user has a password (not OAuth-only)
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account uses OAuth login. Please sign in with Google or GitHub."
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Update last login
    UserCRUD.update_last_login(db, user)

    logger.info(f"User logged in: {user.email}")

    # Generate tokens
    tokens = create_token_pair(user.id, user.email, db)
    set_auth_cookies(response, tokens)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    response: Response,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    Returns new access and refresh tokens.
    """
    # Get refresh token from body or cookie
    refresh_token_value = request.refresh_token or http_request.cookies.get("refresh_token")
    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )

    # Decode refresh token
    payload = decode_token(refresh_token_value)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Check if token exists and is valid
    token_hash = hash_token(refresh_token_value)
    stored_token = RefreshTokenCRUD.get_by_hash(db, token_hash)

    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked"
        )

    if stored_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    # Get user
    user = UserCRUD.get_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled"
        )

    # Revoke old refresh token
    RefreshTokenCRUD.revoke(db, stored_token)

    # Generate new tokens
    tokens = create_token_pair(user.id, user.email, db)
    set_auth_cookies(response, tokens)
    return TokenResponse(**tokens)


@router.post("/logout")
async def logout(
    request: RefreshRequest,
    response: Response,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Logout by revoking the refresh token.
    """
    refresh_token_value = request.refresh_token or http_request.cookies.get("refresh_token")
    if refresh_token_value:
        token_hash = hash_token(refresh_token_value)
        stored_token = RefreshTokenCRUD.get_by_hash(db, token_hash)

        if stored_token:
            RefreshTokenCRUD.revoke(db, stored_token)

    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's information.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        oauth_provider=current_user.oauth_provider,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat()
    )


# ============================================================================
# OAUTH ENDPOINTS
# ============================================================================

@router.get("/oauth/google")
async def google_oauth_redirect():
    """
    Get Google OAuth authorization URL.

    Redirect users to this URL to start Google OAuth flow.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    state = generate_oauth_state("google")
    auth_url = get_google_auth_url(state, f"{OAUTH_REDIRECT_URL}/google")

    return {
        "auth_url": auth_url,
        "state": state
    }


@router.post("/oauth/google/callback", response_model=TokenResponse)
async def google_oauth_callback(
    request: OAuthCallbackRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback.

    Exchange authorization code for tokens and create/update user.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    # Validate OAuth state (CSRF protection)
    if not request.state or not validate_oauth_state(request.state):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OAuth state"
        )

    # Exchange code for access token
    redirect_uri = request.redirect_uri or f"{OAUTH_REDIRECT_URL}/google"
    access_token = await exchange_google_code(request.code, redirect_uri)

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code"
        )

    # Get user info from Google
    google_user = await get_google_user_info(access_token)

    if not google_user or not google_user.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user information from Google"
        )

    email = google_user["email"]
    google_id = google_user.get("id")
    name = google_user.get("name")
    avatar = google_user.get("picture")

    # Find or create user
    user = UserCRUD.get_by_oauth(db, OAuthProvider.GOOGLE.value, google_id)

    if not user:
        # Check if email exists with different provider
        existing_user = UserCRUD.get_by_email(db, email)
        if existing_user:
            # Link Google to existing account
            existing_user.oauth_provider = OAuthProvider.GOOGLE.value
            existing_user.oauth_id = google_id
            existing_user.avatar_url = avatar
            if not existing_user.name:
                existing_user.name = name
            db.commit()
            user = existing_user
        else:
            # Create new user
            user = UserCRUD.create(
                db=db,
                email=email,
                oauth_provider=OAuthProvider.GOOGLE.value,
                oauth_id=google_id,
                name=name
            )
            user.avatar_url = avatar
            db.commit()

    # Update last login
    UserCRUD.update_last_login(db, user)

    logger.info(f"Google OAuth login: {user.email}")

    # Generate tokens
    tokens = create_token_pair(user.id, user.email, db)
    set_auth_cookies(response, tokens)
    return TokenResponse(**tokens)


@router.get("/oauth/github")
async def github_oauth_redirect():
    """
    Get GitHub OAuth authorization URL.

    Redirect users to this URL to start GitHub OAuth flow.
    """
    if not GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured"
        )

    state = generate_oauth_state("github")
    auth_url = get_github_auth_url(state)

    return {
        "auth_url": auth_url,
        "state": state
    }


@router.post("/oauth/github/callback", response_model=TokenResponse)
async def github_oauth_callback(
    request: OAuthCallbackRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Handle GitHub OAuth callback.

    Exchange authorization code for tokens and create/update user.
    """
    if not GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured"
        )

    # Validate OAuth state (CSRF protection)
    if not request.state or not validate_oauth_state(request.state):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OAuth state"
        )

    # Exchange code for access token
    access_token = await exchange_github_code(request.code)

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code"
        )

    # Get user info from GitHub
    github_user = await get_github_user_info(access_token)

    if not github_user or not github_user.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user information from GitHub. Make sure your email is public or grant email permission."
        )

    email = github_user["email"]
    github_id = str(github_user.get("id"))
    name = github_user.get("name") or github_user.get("login")
    avatar = github_user.get("avatar_url")

    # Find or create user
    user = UserCRUD.get_by_oauth(db, OAuthProvider.GITHUB.value, github_id)

    if not user:
        # Check if email exists with different provider
        existing_user = UserCRUD.get_by_email(db, email)
        if existing_user:
            # Link GitHub to existing account
            existing_user.oauth_provider = OAuthProvider.GITHUB.value
            existing_user.oauth_id = github_id
            existing_user.avatar_url = avatar
            if not existing_user.name:
                existing_user.name = name
            db.commit()
            user = existing_user
        else:
            # Create new user
            user = UserCRUD.create(
                db=db,
                email=email,
                oauth_provider=OAuthProvider.GITHUB.value,
                oauth_id=github_id,
                name=name
            )
            user.avatar_url = avatar
            db.commit()

    # Update last login
    UserCRUD.update_last_login(db, user)

    logger.info(f"GitHub OAuth login: {user.email}")

    # Generate tokens
    tokens = create_token_pair(user.id, user.email, db)
    set_auth_cookies(response, tokens)
    return TokenResponse(**tokens)


@router.get("/oauth/config")
async def get_oauth_config():
    """
    Get OAuth configuration for frontend.

    Returns which OAuth providers are enabled.
    """
    return {
        "google_enabled": bool(GOOGLE_CLIENT_ID),
        "github_enabled": bool(GITHUB_CLIENT_ID)
    }
