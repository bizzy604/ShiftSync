"""
MODULE: /apps/api/app/modules/skills/router.py

FUNCTION:
    Exposes skills domain HTTP endpoints through a thin modular route layer.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/skills/router.py

IMPORTANCE:
    This route layer is the pilot migration boundary proving domain modules can be adopted
    without breaking external API contracts.
"""

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, require_roles
from app.modules.skills.schemas import SkillCreateRequest
from app.modules.skills.service import (
    create_skill as create_skill_record,
    delete_skill as delete_skill_record,
    list_skills as list_skill_records,
)
from app.schemas.shift import ShiftRequiredSkill


router = APIRouter()


async def list_skills() -> list[ShiftRequiredSkill]:
    """Return skill catalog entries sorted by name."""

    skills = await list_skill_records()
    return [ShiftRequiredSkill(id=item.id, name=item.name) for item in skills]


async def create_skill(
    payload: SkillCreateRequest,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> ShiftRequiredSkill:
    """Create a new skill catalog entry for administrators."""

    skill = await create_skill_record(name=payload.name, actor_id=current_user.id)
    return ShiftRequiredSkill(id=skill.id, name=skill.name)


async def delete_skill(
    skill_id: str,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> dict[str, bool]:
    """Delete a skill entry when no references exist."""

    await delete_skill_record(skill_id=skill_id, actor_id=current_user.id)
    return {"deleted": True}


router.add_api_route("", list_skills, methods=["GET"], response_model=list[ShiftRequiredSkill])
router.add_api_route("", create_skill, methods=["POST"], response_model=ShiftRequiredSkill)
router.add_api_route("/{skill_id}", delete_skill, methods=["DELETE"])
