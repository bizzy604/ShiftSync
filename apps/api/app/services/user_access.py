"""
MODULE: /apps/api/app/services/user_access.py

FUNCTION:
    Maintains compatibility by re-exporting users-scope service helpers.

DEPENDENCIES:
    - /apps/api/app/modules/users/router.py
    - /apps/api/app/modules/users/router.py

IMPORTANCE:
    This bridge keeps legacy imports stable while users visibility rules live in the
    users domain service layer.
"""

from app.shared.dependencies import CurrentUser

from app.modules.users.service import get_manager_user_scope as get_manager_user_scope_record

async def get_manager_user_scope(current_user: CurrentUser) -> set[str]:
    """Return user ids visible to manager using users-domain visibility rules."""

    return await get_manager_user_scope_record(current_user)
