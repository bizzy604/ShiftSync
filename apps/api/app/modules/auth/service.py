"""
MODULE: /apps/api/app/modules/auth/service.py

FUNCTION:
    Implements auth domain workflows for login/logout/refresh and current-user resolution.

DEPENDENCIES:
    - /apps/api/app/modules/auth/router.py
    - /apps/api/app/modules/auth/__init__.py

IMPORTANCE:
    Centralizing auth rules here ensures session and token behavior remains consistent
    across all authentication endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.security import create_access_token, decode_access_token, verify_password
from app.core.session_store import SessionStore
from app.modules.auth.exceptions import (
    AuthenticationRequiredError,
    AuthUserNotFoundError,
    InvalidCredentialsError,
    InvalidTokenError,
    SessionExpiredError,
)
from app.modules.auth.repository import AuthRepository, get_auth_repository
from app.schemas.auth import AuthenticatedUser, LoginRequest, LoginResponse, RefreshResponse
from app.shared.dependencies import CurrentUser


@dataclass
class CookieSession:
    """Represents auth cookie session values produced by service workflows."""

    token: str
    ttl_seconds: int


@dataclass
class LoginResult:
    """Represents login endpoint workflow output."""

    payload: LoginResponse
    cookie: CookieSession


@dataclass
class RefreshResult:
    """Represents refresh endpoint workflow output."""

    payload: RefreshResponse
    cookie: CookieSession


def _build_auth_user(user: object, location_ids: list[str]) -> AuthenticatedUser:
    """Convert user record and scoped locations to auth response model."""

    return AuthenticatedUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        location_ids=location_ids,
    )


async def _issue_cookie_session(
    *,
    user_id: str,
    role: str,
    location_ids: list[str],
    session_store: SessionStore,
) -> CookieSession:
    """Create token/session pair and persist server-side session state."""

    token, sid, expires_at = create_access_token(
        user_id=user_id,
        role=role,
        location_ids=location_ids,
    )
    ttl_seconds = int((expires_at - datetime.now(tz=timezone.utc)).total_seconds())
    await session_store.set(f"session:{sid}", user_id, ttl_seconds)
    return CookieSession(token=token, ttl_seconds=ttl_seconds)


# PATTERN: Transaction Script
# Each auth workflow orchestrates repository reads and session/token side effects.
async def login(
    *,
    payload: LoginRequest,
    session_store: SessionStore,
    repository: AuthRepository | None = None,
) -> LoginResult:
    """Authenticate user credentials and issue session-backed cookie token."""

    repo = repository or get_auth_repository()
    user = await repo.find_user_by_email(payload.email)
    if user is None or not user.is_active:
        raise InvalidCredentialsError("Invalid credentials.")
    if not verify_password(payload.password, user.password_hash):
        raise InvalidCredentialsError("Invalid credentials.")

    location_ids: list[str] = []
    if user.role == "manager":
        location_ids = [assignment.location_id for assignment in user.manager_location_assignments]

    cookie = await _issue_cookie_session(
        user_id=user.id,
        role=user.role,
        location_ids=location_ids,
        session_store=session_store,
    )
    return LoginResult(payload=LoginResponse(user=_build_auth_user(user, location_ids)), cookie=cookie)


async def logout(
    *,
    token: str | None,
    session_store: SessionStore,
) -> None:
    """Invalidate existing server-side session for the presented cookie token."""

    if token is None:
        return
    try:
        payload = decode_access_token(token)
        sid = payload.get("sid")
        if sid:
            await session_store.delete(f"session:{sid}")
    except ValueError:
        return


async def refresh_token(
    *,
    token: str | None,
    session_store: SessionStore,
    repository: AuthRepository | None = None,
) -> RefreshResult:
    """Rotate token/session pair while preserving auth principal scope."""

    if not token:
        raise AuthenticationRequiredError("Authentication required.")

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise InvalidTokenError("Invalid token.") from exc

    sid = payload.get("sid")
    if not sid or not await session_store.exists(f"session:{sid}"):
        raise SessionExpiredError("Session expired.")

    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or not role:
        raise InvalidTokenError("Invalid token.")

    repo = repository or get_auth_repository()
    if role == "manager":
        location_ids = await repo.list_manager_location_ids(user_id)
    else:
        location_ids = payload.get("location_ids", [])
        if not isinstance(location_ids, list):
            location_ids = []
        location_ids = [item for item in location_ids if isinstance(item, str)]

    await session_store.delete(f"session:{sid}")
    cookie = await _issue_cookie_session(
        user_id=user_id,
        role=role,
        location_ids=location_ids,
        session_store=session_store,
    )
    return RefreshResult(payload=RefreshResponse(refreshed=True), cookie=cookie)


async def get_me(
    *,
    current_user: CurrentUser,
    repository: AuthRepository | None = None,
) -> LoginResponse:
    """Return authenticated user's profile payload."""

    repo = repository or get_auth_repository()
    user = await repo.find_user_by_id(current_user.id)
    if user is None:
        raise AuthUserNotFoundError("User not found.")

    location_ids: list[str] = []
    if user.role == "manager":
        location_ids = [assignment.location_id for assignment in user.manager_location_assignments]
    return LoginResponse(user=_build_auth_user(user, location_ids))

