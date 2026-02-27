"""
MODULE: /apps/api/app/modules/users/repository.py

FUNCTION:
    Provides persistence operations for users, skills, certifications, and availability.

DEPENDENCIES:
    - /apps/api/app/modules/users/service.py

IMPORTANCE:
    Repository isolation keeps users-domain orchestration logic focused on workflows while
    hiding database specifics.
"""

from __future__ import annotations

from typing import Any

from app.core.database import prisma


class UsersRepository:
    """Repository abstraction for users-domain persistence operations."""

    def __init__(self, db: Any | None = None) -> None:
        """Bind repository operations to a database client or transaction handle."""

        self._db = db or prisma

    async def find_many_users(
        self,
        *,
        where: dict[str, Any],
        skip: int,
        take: int,
    ) -> list[object]:
        """Return users matching filter criteria."""

        return await self._db.user.find_many(where=where, skip=skip, take=take, order={"name": "asc"})

    async def count_users(self, *, where: dict[str, Any]) -> int:
        """Return count of users matching filter criteria."""

        return await self._db.user.count(where=where)

    async def find_user_by_email(self, email: str) -> object | None:
        """Return one user by email when it exists."""

        return await self._db.user.find_unique(where={"email": email})

    async def find_user_by_id(self, user_id: str) -> object | None:
        """Return one user by id when it exists."""

        return await self._db.user.find_unique(where={"id": user_id})

    async def create_user(self, data: dict[str, Any]) -> object:
        """Create one user record."""

        return await self._db.user.create(data=data)

    async def update_user(self, *, user_id: str, data: dict[str, Any]) -> object:
        """Update one user record."""

        return await self._db.user.update(where={"id": user_id}, data=data)

    async def list_location_certifications(self, *, location_id: str) -> list[object]:
        """Return active user-location certifications for one location."""

        return await self._db.userlocationcertification.find_many(
            where={"location_id": location_id, "revoked_at": None},
        )

    async def list_users_for_skill(self, *, skill_id: str) -> list[object]:
        """Return user-skill links for one skill id."""

        return await self._db.userskill.find_many(where={"skill_id": skill_id})

    async def list_manager_scope_certifications(self, *, location_ids: list[str]) -> list[object]:
        """Return active certifications in a manager's owned locations."""

        return await self._db.userlocationcertification.find_many(
            where={"location_id": {"in": location_ids}, "revoked_at": None},
        )

    async def list_user_skills(self, *, user_id: str) -> list[object]:
        """Return all user-skill links including skill relation."""

        return await self._db.userskill.find_many(where={"user_id": user_id}, include={"skill": True})

    async def find_skill(self, *, skill_id: str) -> object | None:
        """Return one skill by id when it exists."""

        return await self._db.skill.find_unique(where={"id": skill_id})

    async def find_user_skill_link(self, *, user_id: str, skill_id: str) -> object | None:
        """Return one user-skill link by composite key."""

        return await self._db.userskill.find_unique(
            where={"user_id_skill_id": {"user_id": user_id, "skill_id": skill_id}}
        )

    async def create_user_skill_link(self, *, user_id: str, skill_id: str) -> object:
        """Create one user-skill link record."""

        return await self._db.userskill.create(data={"user_id": user_id, "skill_id": skill_id})

    async def delete_user_skill_link(self, *, user_id: str, skill_id: str) -> None:
        """Delete one user-skill link record by composite key."""

        await self._db.userskill.delete(where={"user_id_skill_id": {"user_id": user_id, "skill_id": skill_id}})

    async def list_user_certifications(self, *, user_id: str) -> list[object]:
        """Return user certifications including location relation."""

        return await self._db.userlocationcertification.find_many(
            where={"user_id": user_id},
            include={"location": True},
        )

    async def find_location(self, *, location_id: str) -> object | None:
        """Return one location by id when it exists."""

        return await self._db.location.find_unique(where={"id": location_id})

    async def upsert_user_certification(self, *, user_id: str, location_id: str) -> object:
        """Create or restore a user-location certification."""

        return await self._db.userlocationcertification.upsert(
            where={"user_id_location_id": {"user_id": user_id, "location_id": location_id}},
            data={
                "create": {
                    "user_id": user_id,
                    "location_id": location_id,
                },
                "update": {
                    "revoked_at": None,
                    "revoked_by": None,
                },
            },
        )

    async def find_user_certification(self, *, user_id: str, location_id: str) -> object | None:
        """Return one user-location certification by composite key."""

        return await self._db.userlocationcertification.find_unique(
            where={"user_id_location_id": {"user_id": user_id, "location_id": location_id}}
        )

    async def revoke_user_certification(
        self,
        *,
        user_id: str,
        location_id: str,
        revoked_at: object,
        revoked_by: str,
    ) -> None:
        """Set revoked metadata for a user-location certification."""

        await self._db.userlocationcertification.update(
            where={"user_id_location_id": {"user_id": user_id, "location_id": location_id}},
            data={"revoked_at": revoked_at, "revoked_by": revoked_by},
        )

    async def list_active_assignments_for_user(self, *, user_id: str) -> list[object]:
        """Return active assigned shift-assignment rows for one user."""

        return await self._db.shiftassignment.find_many(
            where={"user_id": user_id, "status": "assigned"},
            include={"shift": True},
        )

    async def update_shift_assignment(
        self,
        *,
        assignment_id: str,
        version: int,
        override_reason: str,
    ) -> None:
        """Update assignment status for auto-unassignment workflows."""

        await self._db.shiftassignment.update(
            where={"id": assignment_id},
            data={"status": "removed", "version": version, "override_reason": override_reason},
        )

    async def list_manager_links_for_location(self, *, location_id: str) -> list[object]:
        """Return manager-location links for a location."""

        return await self._db.managerlocationassignment.find_many(where={"location_id": location_id})

    async def list_manager_links_for_locations(self, *, location_ids: list[str]) -> list[object]:
        """Return manager-location links for a set of locations."""

        return await self._db.managerlocationassignment.find_many(where={"location_id": {"in": location_ids}})

    async def list_user_availability(self, *, user_id: str) -> list[object]:
        """Return all availability rows for a user ordered by creation time."""

        return await self._db.availability.find_many(where={"user_id": user_id}, order={"created_at": "asc"})

    async def delete_user_availability(self, *, user_id: str) -> None:
        """Delete all availability rows for a user."""

        await self._db.availability.delete_many(where={"user_id": user_id})

    async def create_user_availability_many(self, *, data: list[dict[str, Any]]) -> None:
        """Bulk create availability rows for a user."""

        if data:
            await self._db.availability.create_many(data=data)

    async def list_active_user_certifications(self, *, user_id: str) -> list[object]:
        """Return active certifications for one user."""

        return await self._db.userlocationcertification.find_many(
            where={"user_id": user_id, "revoked_at": None},
        )


def get_users_repository(db: Any | None = None) -> UsersRepository:
    """Return a repository instance bound to the provided database context."""

    return UsersRepository(db=db)

