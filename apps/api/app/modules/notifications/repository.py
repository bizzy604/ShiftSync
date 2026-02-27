"""
MODULE: /apps/api/app/modules/notifications/repository.py

FUNCTION:
    Provides persistence operations for notifications and user preferences.

DEPENDENCIES:
    - /apps/api/app/modules/notifications/service.py

IMPORTANCE:
    Repository isolation keeps domain logic decoupled from persistence mechanics and
    improves testability.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database import prisma


class NotificationsRepository:
    """Repository abstraction for notification persistence operations."""

    def __init__(self, db: Any | None = None) -> None:
        """Bind repository operations to a database client or transaction handle."""

        self._db = db or prisma

    async def list_notifications(
        self,
        *,
        where: dict[str, Any],
        skip: int,
        take: int,
    ) -> list[object]:
        """Return notifications matching filters with pagination applied."""

        return await self._db.notification.find_many(
            where=where,
            order={"created_at": "desc"},
            skip=skip,
            take=take,
        )

    async def count_notifications(self, *, where: dict[str, Any]) -> int:
        """Return count of notifications matching a filter."""

        return await self._db.notification.count(where=where)

    async def mark_all_read(self, *, user_id: str, read_at: datetime) -> None:
        """Mark all unread notifications as read for a user."""

        await self._db.notification.update_many(
            where={"user_id": user_id, "read_at": None},
            data={"read_at": read_at},
        )

    async def find_notification(self, notification_id: str) -> object | None:
        """Return one notification by identifier when it exists."""

        return await self._db.notification.find_unique(where={"id": notification_id})

    async def mark_notification_read(self, *, notification_id: str, read_at: datetime) -> None:
        """Mark one notification as read."""

        await self._db.notification.update(
            where={"id": notification_id},
            data={"read_at": read_at},
        )

    async def find_user(self, user_id: str) -> object | None:
        """Return one user by identifier when it exists."""

        return await self._db.user.find_unique(where={"id": user_id})

    async def update_user_notification_preference(self, *, user_id: str, notification_pref: str) -> object:
        """Update and return a user's notification preference."""

        return await self._db.user.update(
            where={"id": user_id},
            data={"notification_pref": notification_pref},
        )


def get_notifications_repository(db: Any | None = None) -> NotificationsRepository:
    """Return a repository instance bound to the provided database context."""

    return NotificationsRepository(db=db)

