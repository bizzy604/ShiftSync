"""
MODULE: /apps/api/app/modules/auth/__init__.py

FUNCTION:
    Defines the public API boundary and exported contracts for the auth domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/auth/router.py

IMPORTANCE:
    Exporting a stable surface here prevents external callers from depending on private
    module internals.
"""

from app.modules.auth.router import (
    AuthenticatedUser,
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    get_me,
    login,
    logout,
    refresh_token,
    router,
)
from app.modules.auth.service import (
    get_me as get_me_record,
    login as login_record,
    logout as logout_record,
    refresh_token as refresh_token_record,
)

__all__ = [
    "router",
    "LoginRequest",
    "AuthenticatedUser",
    "LoginResponse",
    "RefreshResponse",
    "login",
    "logout",
    "refresh_token",
    "get_me",
    "login_record",
    "logout_record",
    "refresh_token_record",
    "get_me_record",
]
