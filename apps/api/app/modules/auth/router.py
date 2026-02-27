"""
MODULE: /apps/api/app/modules/auth/router.py

FUNCTION:
    Exposes auth HTTP endpoints through a thin modular route layer.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/auth/router.py

IMPORTANCE:
    This route layer preserves existing `/auth` API contracts while delegating login and
    session workflows to service and repository layers.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.config import get_settings
from app.core.session_store import SessionStore
from app.modules.auth.exceptions import (
    AuthenticationRequiredError,
    AuthUserNotFoundError,
    InvalidCredentialsError,
    InvalidTokenError,
    SessionExpiredError,
)
from app.modules.auth.schemas import AuthenticatedUser, LoginRequest, LoginResponse, RefreshResponse
from app.modules.auth.service import (
    get_me as get_me_record,
    login as login_record,
    logout as logout_record,
    refresh_token as refresh_token_record,
)
from app.shared.dependencies import CurrentUser, get_current_user, get_session_store


router = APIRouter()


async def login(
    payload: LoginRequest,
    response: Response,
    session_store: SessionStore = Depends(get_session_store),
) -> LoginResponse:
    """Authenticate user credentials and issue cookie-based session token."""

    try:
        result = await login_record(payload=payload, session_store=session_store)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.") from exc

    settings = get_settings()
    response.set_cookie(
        key=settings.token_cookie_name,
        value=result.cookie.token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=result.cookie.ttl_seconds,
    )
    return result.payload


async def logout(
    request: Request,
    response: Response,
    session_store: SessionStore = Depends(get_session_store),
) -> dict[str, bool]:
    """Invalidate session token and clear cookie."""

    settings = get_settings()
    token = request.cookies.get(settings.token_cookie_name)
    await logout_record(token=token, session_store=session_store)

    response.delete_cookie(
        settings.token_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    return {"logged_out": True}


async def refresh_token(
    request: Request,
    response: Response,
    session_store: SessionStore = Depends(get_session_store),
) -> RefreshResponse:
    """Rotate auth token/session and return refresh status."""

    settings = get_settings()
    token = request.cookies.get(settings.token_cookie_name)
    try:
        result = await refresh_token_record(token=token, session_store=session_store)
    except AuthenticationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.") from exc
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
    except SessionExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.") from exc

    response.set_cookie(
        key=settings.token_cookie_name,
        value=result.cookie.token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=result.cookie.ttl_seconds,
    )
    return result.payload


async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> LoginResponse:
    """Return current authenticated user payload."""

    try:
        return await get_me_record(current_user=current_user)
    except AuthUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.") from exc


router.add_api_route("/login", login, methods=["POST"], response_model=LoginResponse)
router.add_api_route("/logout", logout, methods=["POST"])
router.add_api_route("/refresh", refresh_token, methods=["POST"], response_model=RefreshResponse)
router.add_api_route("/me", get_me, methods=["GET"], response_model=LoginResponse)
