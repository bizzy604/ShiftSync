"""
MODULE: /apps/api/app/services/contracts.py

FUNCTION:
    Implements reusable domain service logic for `contracts` workflows.

DEPENDENCIES:
    - /apps/api/app/services/__init__.py
    - /apps/api/app/services/drop_expiry.py
    - /apps/api/app/services/notifications.py
    - /apps/api/app/services/skill_catalog.py
    - /apps/api/app/services/swap_lifecycle.py

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class UserReaderProtocol(Protocol):
    """Repository contract for reading user records."""

    async def find_unique(self, *, where: dict[str, Any]) -> object | None:
        """Find one user record matching unique criteria."""
        ...


class NotificationWriterProtocol(Protocol):
    """Repository contract for creating notification records."""

    async def create(self, *, data: dict[str, Any]) -> object:
        """Create one notification record."""
        ...


class NotificationDataClientProtocol(Protocol):
    """Data access contract required by notification creation workflows."""

    user: UserReaderProtocol
    notification: NotificationWriterProtocol


class CountAccessorProtocol(Protocol):
    """Repository contract for count queries."""

    async def count(self, *, where: dict[str, Any]) -> int:
        """Count records matching query filters."""
        ...


class SkillAccessorProtocol(Protocol):
    """Repository contract for skill CRUD used by skill catalog workflows."""

    async def find_many(
        self, *, where: dict[str, Any] | None = None, order: dict[str, str] | None = None
    ) -> list[object]:
        """Find skill records using optional filters and ordering."""
        ...

    async def find_unique(self, *, where: dict[str, Any]) -> object | None:
        """Find one skill record by unique key."""
        ...

    async def create(self, *, data: dict[str, Any]) -> object:
        """Create one skill record."""
        ...

    async def delete(self, *, where: dict[str, Any]) -> object | None:
        """Delete one skill record by unique key."""
        ...


class SkillCatalogClientProtocol(Protocol):
    """Data access contract required by skill catalog service functions."""

    skill: SkillAccessorProtocol
    userskill: CountAccessorProtocol
    shift: CountAccessorProtocol


@runtime_checkable
class RealtimeEmitterProtocol(Protocol):
    """Contract for WebSocket/event fan-out used by services."""

    async def emit_to_user(self, user_id: str, event: str, payload: dict[str, Any]) -> None:
        """Emit a real-time event to a single user."""
        ...

    async def emit_to_users(self, user_ids: list[str], event: str, payload: dict[str, Any]) -> None:
        """Emit a real-time event to multiple users."""
        ...

    async def emit_to_location(
        self, location_id: str, event: str, payload: dict[str, Any]
    ) -> None:
        """Emit a real-time event scoped to a location."""
        ...
