"""
MODULE: /apps/api/app/modules/analytics/repository.py

FUNCTION:
    Provides read-oriented persistence operations for analytics reporting workflows.

DEPENDENCIES:
    - /apps/api/app/modules/analytics/service.py

IMPORTANCE:
    Isolating analytics data access keeps service logic focused on report calculations and
    simplifies testing with repository doubles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database import prisma


class AnalyticsRepository:
    """Repository abstraction for analytics read operations."""

    def __init__(self, db: Any | None = None) -> None:
        """Bind analytics queries to a database client or transaction handle."""

        self._db = db or prisma

    async def find_location(self, location_id: str) -> object | None:
        """Return one location by identifier when it exists."""

        return await self._db.location.find_unique(where={"id": location_id})

    async def list_active_locations(self) -> list[object]:
        """Return all active locations."""

        return await self._db.location.find_many(where={"is_active": True})

    async def list_week_shifts(self, *, location_id: str, week_start: datetime) -> list[object]:
        """Return draft/published shifts for a location and week."""

        return await self._db.shift.find_many(
            where={
                "location_id": location_id,
                "week_start": week_start,
                "status": {"in": ["draft", "published"]},
            },
            order={"start_utc": "asc"},
        )

    async def list_assigned_shift_assignments(self, *, shift_ids: list[str]) -> list[object]:
        """Return assigned shift assignments for target shifts."""

        return await self._db.shiftassignment.find_many(
            where={"shift_id": {"in": shift_ids}, "status": "assigned"},
            include={"user": True, "shift": {"include": {"location": True, "required_skill": True}}},
        )

    async def list_assigned_user_assignments(self, *, user_ids: list[str]) -> list[object]:
        """Return assigned shift assignments for target users."""

        return await self._db.shiftassignment.find_many(
            where={"user_id": {"in": user_ids}, "status": "assigned"},
            include={"shift": True, "user": True},
        )

    async def list_active_staff_certifications(self, *, location_id: str) -> list[object]:
        """Return active user-location certifications including user records."""

        return await self._db.userlocationcertification.find_many(
            where={"location_id": location_id, "revoked_at": None},
            include={"user": True},
        )

    async def list_shifts_in_date_range(
        self,
        *,
        location_id: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[object]:
        """Return shifts for a location within an inclusive date range."""

        return await self._db.shift.find_many(
            where={
                "location_id": location_id,
                "shift_date": {"gte": start_at, "lte": end_at},
            },
            order={"start_utc": "asc"},
        )

    async def list_active_shifts_at(
        self,
        *,
        location_ids: list[str],
        now: datetime,
    ) -> list[object]:
        """Return active shifts at a given point in time for scoped locations."""

        return await self._db.shift.find_many(
            where={
                "location_id": {"in": location_ids},
                "start_utc": {"lte": now},
                "end_utc": {"gt": now},
                "status": {"in": ["draft", "published"]},
            },
            include={"location": True, "required_skill": True},
        )


def get_analytics_repository(db: Any | None = None) -> AnalyticsRepository:
    """Return a repository instance bound to the provided database context."""

    return AnalyticsRepository(db=db)

