"""
MODULE: /apps/api/app/modules/skills/service.py

FUNCTION:
    Implements skills domain business workflows using repository and audit boundaries.

DEPENDENCIES:
    - /apps/api/app/modules/skills/router.py
    - /apps/api/app/modules/skills/__init__.py
    - /apps/api/app/services/skill_catalog.py

IMPORTANCE:
    This module centralizes skill-catalog rules so route handlers stay thin while maintaining
    transactional consistency and typed error handling.
"""

from __future__ import annotations

from app.core.database import prisma
from app.modules.skills.exceptions import (
    SkillAlreadyExistsError,
    SkillInUseError,
    SkillNameEmptyError,
    SkillNotFoundError,
)
from app.modules.skills.repository import SkillsRepository, get_skills_repository
from app.services.audit import create_audit_log


# PATTERN: Transaction Script
# Each service function coordinates validation, persistence, and audit side effects.
async def list_skills(*, repository: SkillsRepository | None = None) -> list[object]:
    """Return all skills sorted by name."""

    repo = repository or get_skills_repository()
    return await repo.list_skills()


async def create_skill(
    *,
    name: str,
    actor_id: str,
    repository: SkillsRepository | None = None,
) -> object:
    """Create a skill record with duplicate-name checks and audit logging."""

    normalized_name = name.strip()
    if not normalized_name:
        raise SkillNameEmptyError()

    base_repo = repository or get_skills_repository(db=prisma)
    existing = await base_repo.list_skills()
    if any(item.name.lower() == normalized_name.lower() for item in existing):
        raise SkillAlreadyExistsError(normalized_name)

    if repository is not None:
        skill = await repository.create_skill(normalized_name)
        await create_audit_log(
            actor_id=actor_id,
            action_type="skill.catalog.add",
            entity_type="skill",
            entity_id=skill.id,
            after_state={"name": skill.name},
            db=repository._db,
        )
        return skill

    async with prisma.tx() as tx:
        tx_repo = get_skills_repository(db=tx)
        skill = await tx_repo.create_skill(normalized_name)
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
    *,
    skill_id: str,
    actor_id: str,
    repository: SkillsRepository | None = None,
) -> None:
    """Delete a skill when it is not referenced by users or shifts."""

    base_repo = repository or get_skills_repository(db=prisma)
    skill = await base_repo.find_skill(skill_id)
    if skill is None:
        raise SkillNotFoundError(skill_id)

    user_links = await base_repo.count_user_links(skill_id)
    shift_links = await base_repo.count_shift_links(skill_id)
    if user_links > 0 or shift_links > 0:
        raise SkillInUseError()

    if repository is not None:
        await repository.delete_skill(skill_id)
        await create_audit_log(
            actor_id=actor_id,
            action_type="skill.catalog.remove",
            entity_type="skill",
            entity_id=skill_id,
            before_state={"name": skill.name},
            db=repository._db,
        )
        return

    async with prisma.tx() as tx:
        tx_repo = get_skills_repository(db=tx)
        await tx_repo.delete_skill(skill_id)
        await create_audit_log(
            actor_id=actor_id,
            action_type="skill.catalog.remove",
            entity_type="skill",
            entity_id=skill_id,
            before_state={"name": skill.name},
            db=tx,
        )
