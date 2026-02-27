"""
MODULE: /apps/api/app/api/deps.py

FUNCTION:
    Maintains compatibility by re-exporting shared authentication dependencies.

DEPENDENCIES:
    - /apps/api/app/modules/assignments/router.py
    - /apps/api/app/modules/shifts/router.py
    - /apps/api/app/modules/swaps/router.py
    - /apps/api/tests/integration/*

IMPORTANCE:
    This bridge lets existing imports continue working while auth/session checks are
    centralized in `app.shared.dependencies`.
"""

from app.shared.dependencies.auth import (
    CurrentUser,
    ensure_manager_location_access,
    ensure_self_or_admin,
    get_current_user,
    get_session_store,
    require_roles,
)

__all__ = [
    "CurrentUser",
    "get_session_store",
    "get_current_user",
    "require_roles",
    "ensure_self_or_admin",
    "ensure_manager_location_access",
]
