"""
MODULE: /apps/api/app/api/routes/auth.py

FUNCTION:
    Defines FastAPI endpoints and request/response orchestration for the `auth` domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py

IMPORTANCE:
    This module directly shapes externally visible API behavior and role-based access flows.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import CurrentUser, get_current_user, get_session_store
from app.core.config import get_settings
from app.core.database import prisma
from app.core.security import create_access_token, decode_access_token, verify_password
from app.core.session_store import SessionStore
from app.schemas.auth import AuthenticatedUser, LoginRequest, LoginResponse, RefreshResponse


router = APIRouter()


def _build_auth_user(user: object, location_ids: list[str]) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        location_ids=location_ids,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session_store: SessionStore = Depends(get_session_store),
) -> LoginResponse:
    """Login.
    
    Args:
        payload: Validated request payload model.
        response: Mutable HTTP response object for cookies/headers.
        session_store: Session store dependency used for token/session checks.
    
    Returns:
        Result typed as `LoginResponse`.
    """
    user = await prisma.user.find_unique(
        where={"email": payload.email},
        include={"manager_location_assignments": True},
    )
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    location_ids = []
    if user.role == "manager":
        location_ids = [assignment.location_id for assignment in user.manager_location_assignments]

    token, sid, expires_at = create_access_token(
        user_id=user.id,
        role=user.role,
        location_ids=location_ids,
    )
    ttl_seconds = int((expires_at - datetime.now(tz=timezone.utc)).total_seconds())
    await session_store.set(f"session:{sid}", user.id, ttl_seconds)

    settings = get_settings()
    response.set_cookie(
        key=settings.token_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=ttl_seconds,
    )
    return LoginResponse(user=_build_auth_user(user, location_ids))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session_store: SessionStore = Depends(get_session_store),
) -> dict[str, bool]:
    """Logout.
    
    Args:
        request: Incoming FastAPI request context.
        response: Mutable HTTP response object for cookies/headers.
        session_store: Session store dependency used for token/session checks.
    
    Returns:
        True when the operation succeeds, otherwise False.
    """
    settings = get_settings()
    token = request.cookies.get(settings.token_cookie_name)
    if token:
        try:
            payload = decode_access_token(token)
            sid = payload.get("sid")
            if sid:
                await session_store.delete(f"session:{sid}")
        except ValueError:
            pass

    response.delete_cookie(
        settings.token_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    return {"logged_out": True}


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: Request,
    response: Response,
    session_store: SessionStore = Depends(get_session_store),
) -> RefreshResponse:
    """Refresh token.
    
    Args:
        request: Incoming FastAPI request context.
        response: Mutable HTTP response object for cookies/headers.
        session_store: Session store dependency used for token/session checks.
    
    Returns:
        Result typed as `RefreshResponse`.
    """
    settings = get_settings()
    token = request.cookies.get(settings.token_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    sid = payload.get("sid")
    if not sid or not await session_store.exists(f"session:{sid}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")

    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    if role == "manager":
        assignments = await prisma.managerlocationassignment.find_many(where={"manager_id": user_id})
        location_ids = sorted({item.location_id for item in assignments})
    else:
        location_ids = payload.get("location_ids", [])
        if not isinstance(location_ids, list):
            location_ids = []
        location_ids = [item for item in location_ids if isinstance(item, str)]

    await session_store.delete(f"session:{sid}")

    new_token, new_sid, expires_at = create_access_token(
        user_id=user_id,
        role=role,
        location_ids=location_ids,
    )
    ttl_seconds = int((expires_at - datetime.now(tz=timezone.utc)).total_seconds())
    await session_store.set(f"session:{new_sid}", user_id, ttl_seconds)

    response.set_cookie(
        key=settings.token_cookie_name,
        value=new_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=ttl_seconds,
    )
    return RefreshResponse(refreshed=True)


@router.get("/me", response_model=LoginResponse)
async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> LoginResponse:
    """Get me.
    
    Args:
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `LoginResponse`.
    """
    user = await prisma.user.find_unique(
        where={"id": current_user.id},
        include={"manager_location_assignments": True},
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    location_ids = []
    if user.role == "manager":
        location_ids = [assignment.location_id for assignment in user.manager_location_assignments]

    return LoginResponse(user=_build_auth_user(user, location_ids))
