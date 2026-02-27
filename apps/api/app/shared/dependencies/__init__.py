"""
MODULE: /apps/api/app/shared/dependencies/__init__.py

FUNCTION:
    Exposes shared cross-domain dependency helpers.

DEPENDENCIES:
    - /apps/api/app/api/deps.py
    - /apps/api/app/modules/auth/router.py
    - /apps/api/app/modules/users/router.py

IMPORTANCE:
    Shared utilities reduce duplication while preserving clear domain boundaries.
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
