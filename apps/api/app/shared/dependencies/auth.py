"""
MODULE: /apps/api/app/shared/dependencies/auth.py

FUNCTION:
    Centralizes session and JWT dependency helpers used across protected API routes.

DEPENDENCIES:
    - /apps/api/app/api/deps.py
    - /apps/api/app/modules/auth/router.py
    - /apps/api/app/modules/users/router.py

IMPORTANCE:
    This module is the shared authentication boundary. Keeping token decoding and
    session validation here ensures all domains enforce the same auth semantics.
"""

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from app.core.config import get_settings
from app.core.database import prisma
from app.core.security import decode_access_token
from app.core.session_store import SessionStore


@dataclass
class CurrentUser:
    """Current authenticated principal resolved from session-backed JWT token."""

    id: str
    role: str
    location_ids: list[str]


def get_session_store(request: Request) -> SessionStore:
    """Return request-bound session store dependency."""

    return request.app.state.session_store


async def get_current_user(
    request: Request,
    session_store: SessionStore = Depends(get_session_store),
) -> CurrentUser:
    """Resolve current user from signed token and active server-side session."""

    settings = get_settings()
    token = request.cookies.get(settings.token_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    sid = payload.get("sid")
    if not sid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token.")

    if not await session_store.exists(f"session:{sid}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")

    # Slide session TTL on activity to enforce inactivity-based expiration.
    await session_store.touch(
        f"session:{sid}",
        settings.access_token_expire_minutes * 60,
    )

    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    location_ids = payload.get("location_ids", [])
    if not isinstance(location_ids, list):
        location_ids = []

    if role == "manager":
        manager_assignments = await prisma.managerlocationassignment.find_many(
            where={"manager_id": user_id},
        )
        location_ids = sorted({item.location_id for item in manager_assignments})
    else:
        location_ids = [item for item in location_ids if isinstance(item, str)]

    return CurrentUser(id=user_id, role=role, location_ids=location_ids)


def require_roles(*roles: str) -> Callable[[CurrentUser], CurrentUser]:
    """Create a dependency that allows only the specified roles."""

    async def _require_role(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
        return current_user

    return _require_role


def ensure_self_or_admin(current_user: CurrentUser, target_user_id: str) -> None:
    """Raise 403 when user is neither admin nor owner of the target user id."""

    if current_user.role != "admin" and current_user.id != target_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def ensure_manager_location_access(current_user: CurrentUser, location_id: str) -> None:
    """Raise 403 when a manager attempts to access an unowned location."""

    if current_user.role == "admin":
        return
    if current_user.role != "manager":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role required.")
    if location_id not in current_user.location_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager does not own this location.")
