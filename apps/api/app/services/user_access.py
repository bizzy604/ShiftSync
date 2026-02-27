"""
MODULE: /apps/api/app/services/user_access.py

FUNCTION:
    Implements reusable domain service logic for `user_access` workflows.

DEPENDENCIES:
    - /apps/api/app/api/routes/users.py

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""

from app.api.deps import CurrentUser
from app.core.database import prisma


async def get_manager_user_scope(current_user: CurrentUser) -> set[str]:
    """
    Returns user IDs visible to a manager via active certifications in any assigned location.
    """

    if current_user.role == "admin":
        users = await prisma.user.find_many()
        return {user.id for user in users}

    if current_user.role != "manager" or not current_user.location_ids:
        return {current_user.id}

    certs = await prisma.userlocationcertification.find_many(
        where={
            "location_id": {"in": current_user.location_ids},
            "revoked_at": None,
        },
    )

    user_ids = {cert.user_id for cert in certs}
    user_ids.add(current_user.id)
    return user_ids
