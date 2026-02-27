"""
MODULE: /apps/api/app/modules/auth/repository.py

FUNCTION:
    Provides persistence operations for authentication and identity lookup workflows.

DEPENDENCIES:
    - /apps/api/app/modules/auth/service.py

IMPORTANCE:
    Isolating auth data access keeps service logic focused on token/session workflows and
    improves testability.
"""

from __future__ import annotations

from typing import Any

from app.core.database import prisma


class AuthRepository:
    """Repository abstraction for auth-related data operations."""

    def __init__(self, db: Any | None = None) -> None:
        """Bind repository methods to a database client or transaction handle."""

        self._db = db or prisma

    async def find_user_by_email(self, email: str) -> object | None:
        """Return one user by email including manager location assignments."""

        return await self._db.user.find_unique(
            where={"email": email},
            include={"manager_location_assignments": True},
        )

    async def find_user_by_id(self, user_id: str) -> object | None:
        """Return one user by id including manager location assignments."""

        return await self._db.user.find_unique(
            where={"id": user_id},
            include={"manager_location_assignments": True},
        )

    async def list_manager_location_ids(self, manager_id: str) -> list[str]:
        """Return sorted unique location ids assigned to a manager."""

        assignments = await self._db.managerlocationassignment.find_many(where={"manager_id": manager_id})
        return sorted({item.location_id for item in assignments})


def get_auth_repository(db: Any | None = None) -> AuthRepository:
    """Return a repository instance bound to the provided database context."""

    return AuthRepository(db=db)

