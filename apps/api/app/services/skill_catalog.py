"""
MODULE: /apps/api/app/services/skill_catalog.py

FUNCTION:
    Implements reusable domain service logic for `skill_catalog` workflows.

DEPENDENCIES:
    - /apps/api/app/api/routes/skills.py
    - /apps/api/app/services/__init__.py
    - /apps/api/tests/integration/test_skills_routes.py

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""

from __future__ import annotations

from app.core.database import prisma
from app.services.audit import create_audit_log
from app.services.contracts import SkillCatalogClientProtocol
from app.services.errors import (
    SkillAlreadyExistsError,
    SkillInUseError,
    SkillNameEmptyError,
    SkillNotFoundError,
)


# PATTERN: Transaction Script
# Each function performs one use case end-to-end with explicit transaction scope.
async def list_skills(*, db: SkillCatalogClientProtocol | None = None) -> list[object]:
    """Return all skills sorted by name."""
    client: SkillCatalogClientProtocol = db or prisma
    return await client.skill.find_many(order={"name": "asc"})


async def create_skill(
    *, name: str, actor_id: str, db: SkillCatalogClientProtocol | None = None
) -> object:
    """Create a skill record with duplicate-name protection and audit logging."""
    normalized_name = name.strip()
    if not normalized_name:
        raise SkillNameEmptyError()

    client: SkillCatalogClientProtocol = db or prisma
    existing_skills = await client.skill.find_many()
    if any(item.name.lower() == normalized_name.lower() for item in existing_skills):
        raise SkillAlreadyExistsError(normalized_name)

    if db is not None:
        skill = await client.skill.create(data={"name": normalized_name})
        await create_audit_log(
            actor_id=actor_id,
            action_type="skill.catalog.add",
            entity_type="skill",
            entity_id=skill.id,
            after_state={"name": skill.name},
            db=client,
        )
        return skill

    async with prisma.tx() as tx:
        skill = await tx.skill.create(data={"name": normalized_name})
        await create_audit_log(
            actor_id=actor_id,
            action_type="skill.catalog.add",
            entity_type="skill",
            entity_id=skill.id,
            after_state={"name": skill.name},
            db=tx,
        )
    return skill


async def delete_skill(
    *, skill_id: str, actor_id: str, db: SkillCatalogClientProtocol | None = None
) -> None:
    """Delete an unused skill record and write an audit event."""
    client: SkillCatalogClientProtocol = db or prisma
    skill = await client.skill.find_unique(where={"id": skill_id})
    if skill is None:
        raise SkillNotFoundError(skill_id)

    user_links = await client.userskill.count(where={"skill_id": skill_id})
    shift_links = await client.shift.count(where={"required_skill_id": skill_id})
    if user_links > 0 or shift_links > 0:
        raise SkillInUseError()

    if db is not None:
        await client.skill.delete(where={"id": skill_id})
        await create_audit_log(
            actor_id=actor_id,
            action_type="skill.catalog.remove",
            entity_type="skill",
            entity_id=skill_id,
            before_state={"name": skill.name},
            db=client,
        )
        return

    async with prisma.tx() as tx:
        await tx.skill.delete(where={"id": skill_id})
        await create_audit_log(
            actor_id=actor_id,
            action_type="skill.catalog.remove",
            entity_type="skill",
            entity_id=skill_id,
            before_state={"name": skill.name},
            db=tx,
        )
