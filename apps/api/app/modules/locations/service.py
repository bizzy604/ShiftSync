"""
MODULE: /apps/api/app/modules/locations/service.py

FUNCTION:
    Implements location domain workflows for role-scoped reads and audited mutations.

DEPENDENCIES:
    - /apps/api/app/modules/locations/router.py
    - /apps/api/app/modules/locations/__init__.py

IMPORTANCE:
    Centralizing location rules here preserves authorization and audit consistency while
    keeping route handlers thin.
"""

from __future__ import annotations

from app.api.deps import CurrentUser
from app.core.database import prisma
from app.modules.locations.exceptions import LocationAccessDeniedError, LocationNotFoundError
from app.modules.locations.repository import LocationsRepository, get_locations_repository
from app.schemas.location import LocationCreateRequest, LocationUpdateRequest
from app.services.audit import create_audit_log


# PATTERN: Transaction Script
# Service functions coordinate validation, repository calls, and audit side effects.
async def list_locations(
    *,
    current_user: CurrentUser,
    repository: LocationsRepository | None = None,
) -> list[object]:
    """Return locations visible to the current user role."""

    repo = repository or get_locations_repository()
    if current_user.role == "admin":
        return await repo.list_all_locations()
    if current_user.role == "manager":
        return await repo.list_manager_locations(current_user.id)
    return await repo.list_staff_locations(current_user.id)


async def get_location(
    *,
    location_id: str,
    current_user: CurrentUser,
    repository: LocationsRepository | None = None,
) -> object:
    """Return one location after applying role-specific access checks."""

    repo = repository or get_locations_repository()
    location = await repo.find_location(location_id)
    if location is None:
        raise LocationNotFoundError(location_id)

    if current_user.role == "manager" and location_id not in current_user.location_ids:
        raise LocationAccessDeniedError("Access denied.")

    if current_user.role == "staff":
        cert = await repo.find_staff_location_certification(
            user_id=current_user.id,
            location_id=location_id,
        )
        if cert is None or cert.revoked_at is not None:
            raise LocationAccessDeniedError("Access denied.")

    return location


async def create_location(
    *,
    payload: LocationCreateRequest,
    actor_id: str,
    repository: LocationsRepository | None = None,
) -> object:
    """Create a location and write the corresponding audit log entry."""

    data = payload.model_dump()
    if repository is not None:
        location = await repository.create_location(data)
        await create_audit_log(
            actor_id=actor_id,
            action_type="location.create",
            entity_type="location",
            entity_id=location.id,
            location_id=location.id,
            after_state={
                "name": location.name,
                "address": location.address,
                "iana_timezone": location.iana_timezone,
                "is_active": location.is_active,
            },
            db=repository._db,
        )
        return location

    async with prisma.tx() as tx:
        tx_repo = get_locations_repository(db=tx)
        location = await tx_repo.create_location(data)
        await create_audit_log(
            actor_id=actor_id,
            action_type="location.create",
            entity_type="location",
            entity_id=location.id,
            location_id=location.id,
            after_state={
                "name": location.name,
                "address": location.address,
                "iana_timezone": location.iana_timezone,
                "is_active": location.is_active,
            },
            db=tx,
        )
        return location


async def update_location(
    *,
    location_id: str,
    payload: LocationUpdateRequest,
    actor_id: str,
    repository: LocationsRepository | None = None,
) -> object:
    """Update a location and write an audit log with before/after states."""

    repo = repository or get_locations_repository()
    existing = await repo.find_location(location_id)
    if existing is None:
        raise LocationNotFoundError(location_id)

    data = payload.model_dump(exclude_none=True)
    if repository is not None:
        location = await repository.update_location(location_id=location_id, data=data)
        await create_audit_log(
            actor_id=actor_id,
            action_type="location.update",
            entity_type="location",
            entity_id=location_id,
            location_id=location_id,
            before_state={
                "name": existing.name,
                "address": existing.address,
                "iana_timezone": existing.iana_timezone,
                "is_active": existing.is_active,
            },
            after_state={
                "name": location.name,
                "address": location.address,
                "iana_timezone": location.iana_timezone,
                "is_active": location.is_active,
            },
            db=repository._db,
        )
        return location

    async with prisma.tx() as tx:
        tx_repo = get_locations_repository(db=tx)
        location = await tx_repo.update_location(location_id=location_id, data=data)
        await create_audit_log(
            actor_id=actor_id,
            action_type="location.update",
            entity_type="location",
            entity_id=location_id,
            location_id=location_id,
            before_state={
                "name": existing.name,
                "address": existing.address,
                "iana_timezone": existing.iana_timezone,
                "is_active": existing.is_active,
            },
            after_state={
                "name": location.name,
                "address": location.address,
                "iana_timezone": location.iana_timezone,
                "is_active": location.is_active,
            },
            db=tx,
        )
        return location

