"""
MODULE: /apps/api/app/modules/locations/repository.py

FUNCTION:
    Provides persistence operations for locations and role-scoped location relationships.

DEPENDENCIES:
    - /apps/api/app/modules/locations/service.py

IMPORTANCE:
    Isolating data access in a repository keeps route and service code storage-agnostic and
    easier to test.
"""

from __future__ import annotations

from typing import Any

from app.core.database import prisma


class LocationsRepository:
    """Repository abstraction for location persistence operations."""

    def __init__(self, db: Any | None = None) -> None:
        """Bind repository operations to a database client or transaction handle."""

        self._db = db or prisma

    async def list_all_locations(self) -> list[object]:
        """Return all locations ordered by name."""

        return await self._db.location.find_many(order={"name": "asc"})

    async def list_manager_locations(self, manager_id: str) -> list[object]:
        """Return locations assigned to a manager."""

        assignments = await self._db.managerlocationassignment.find_many(
            where={"manager_id": manager_id},
            include={"location": True},
        )
        return [assignment.location for assignment in assignments if assignment.location is not None]

    async def list_staff_locations(self, user_id: str) -> list[object]:
        """Return active certified locations for a staff user."""

        certs = await self._db.userlocationcertification.find_many(
            where={"user_id": user_id, "revoked_at": None},
            include={"location": True},
        )
        return [cert.location for cert in certs if cert.location is not None]

    async def find_location(self, location_id: str) -> object | None:
        """Return a location by identifier when it exists."""

        return await self._db.location.find_unique(where={"id": location_id})

    async def find_staff_location_certification(self, *, user_id: str, location_id: str) -> object | None:
        """Return one user-location certification record when present."""

        return await self._db.userlocationcertification.find_unique(
            where={"user_id_location_id": {"user_id": user_id, "location_id": location_id}},
        )

    async def create_location(self, data: dict[str, Any]) -> object:
        """Create and return a location record."""

        return await self._db.location.create(data=data)

    async def update_location(self, *, location_id: str, data: dict[str, Any]) -> object:
        """Update and return a location record."""

        return await self._db.location.update(where={"id": location_id}, data=data)


def get_locations_repository(db: Any | None = None) -> LocationsRepository:
    """Return a repository instance bound to the provided database context."""

    return LocationsRepository(db=db)

