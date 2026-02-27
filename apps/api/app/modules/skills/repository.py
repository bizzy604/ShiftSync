"""
MODULE: /apps/api/app/modules/skills/repository.py

FUNCTION:
    Provides persistence operations for skill catalog records and related references.

DEPENDENCIES:
    - /apps/api/app/modules/skills/service.py

IMPORTANCE:
    Isolating persistence operations behind a repository keeps service logic storage-agnostic
    and easier to test.
"""

from __future__ import annotations

from typing import Any

from app.core.database import prisma


class SkillsRepository:
    """Repository abstraction for skill catalog persistence operations."""

    def __init__(self, db: Any | None = None) -> None:
        """Create repository bound to the provided database client or global prisma facade."""

        self._db = db or prisma

    async def list_skills(self) -> list[object]:
        """Return all skills sorted alphabetically."""

        return await self._db.skill.find_many(order={"name": "asc"})

    async def find_skill(self, skill_id: str) -> object | None:
        """Return one skill by identifier when it exists."""

        return await self._db.skill.find_unique(where={"id": skill_id})

    async def create_skill(self, name: str) -> object:
        """Create and return a new skill record."""

        return await self._db.skill.create(data={"name": name})

    async def delete_skill(self, skill_id: str) -> object | None:
        """Delete one skill by identifier."""

        return await self._db.skill.delete(where={"id": skill_id})

    async def count_user_links(self, skill_id: str) -> int:
        """Return number of user-skill associations for the target skill."""

        return await self._db.userskill.count(where={"skill_id": skill_id})

    async def count_shift_links(self, skill_id: str) -> int:
        """Return number of shift records referencing the target skill."""

        return await self._db.shift.count(where={"required_skill_id": skill_id})


def get_skills_repository(db: Any | None = None) -> SkillsRepository:
    """Return a repository instance using the provided database context."""

    return SkillsRepository(db=db)
