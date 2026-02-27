"""
MODULE: /apps/api/app/modules/users/service.py

FUNCTION:
    Provides users-domain shared service helpers for visibility scope and validations.

DEPENDENCIES:
    - /apps/api/app/modules/users/router.py
    - /apps/api/app/services/user_access.py

IMPORTANCE:
    Centralizing scope and validation logic here prevents authorization drift across
    users endpoints and compatibility adapters.
"""

from __future__ import annotations

import re

from app.core.database import prisma
from app.modules.users.exceptions import UserAccessDeniedError, UserInvalidClockTimeError
from app.shared.dependencies import CurrentUser


CLOCK_TIME_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


# PATTERN: Service Layer
# Shared users-domain helpers extracted from route handlers to avoid duplicated logic.
async def get_manager_user_scope(current_user: CurrentUser) -> set[str]:
    """Return user IDs visible to a manager via active certifications in owned locations."""

    if current_user.role == "admin":
        users = await prisma.user.find_many()
        return {user.id for user in users}

    if current_user.role != "manager" or not current_user.location_ids:
        return {current_user.id}

    certs = await prisma.userlocationcertification.find_many(
        where={"location_id": {"in": current_user.location_ids}, "revoked_at": None},
    )
    user_ids = {cert.user_id for cert in certs}
    user_ids.add(current_user.id)
    return user_ids


async def assert_user_visible_to_actor(actor: CurrentUser, target_user_id: str) -> None:
    """Raise when actor is not authorized to access the target user record."""

    if actor.role == "admin" or actor.id == target_user_id:
        return
    if actor.role != "manager":
        raise UserAccessDeniedError("Access denied.")
    visible_ids = await get_manager_user_scope(actor)
    if target_user_id not in visible_ids:
        raise UserAccessDeniedError("Access denied.")


def ensure_clock(clock_time: str | None) -> None:
    """Validate HH:MM clock format when value is provided."""

    if clock_time is None or CLOCK_TIME_REGEX.match(clock_time):
        return
    raise UserInvalidClockTimeError(clock_time)

