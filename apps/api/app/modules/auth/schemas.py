"""
MODULE: /apps/api/app/modules/auth/schemas.py

FUNCTION:
    Re-exports auth request/response schemas for the modular domain boundary.

DEPENDENCIES:
    - /apps/api/app/modules/auth/router.py
    - /apps/api/app/modules/auth/__init__.py

IMPORTANCE:
    Keeping schema imports local to the module improves discoverability while preserving
    existing shared API contract definitions.
"""

from app.schemas.auth import AuthenticatedUser, LoginRequest, LoginResponse, RefreshResponse

__all__ = [
    "LoginRequest",
    "AuthenticatedUser",
    "LoginResponse",
    "RefreshResponse",
]

