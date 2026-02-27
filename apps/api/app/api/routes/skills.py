"""
MODULE: /apps/api/app/api/routes/skills.py

FUNCTION:
    Defines FastAPI endpoints and request/response orchestration for the `skills` domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/tests/integration/test_skills_routes.py

IMPORTANCE:
    This module directly shapes externally visible API behavior and role-based access flows.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, require_roles
from app.schemas.shift import ShiftRequiredSkill
from app.services.skill_catalog import (
    create_skill as create_skill_record,
    delete_skill as delete_skill_record,
    list_skills as list_skill_records,
)

router = APIRouter()


class SkillCreateRequest(BaseModel):
    """SkillCreateRequest type."""
    name: str = Field(min_length=1, max_length=100)


@router.get("", response_model=list[ShiftRequiredSkill])
async def list_skills() -> list[ShiftRequiredSkill]:
    """List skills.
    
    Returns:
        List of resulting items.
    """
    skills = await list_skill_records()
    return [
        ShiftRequiredSkill(
            id=skill.id,
            name=skill.name,
        )
        for skill in skills
    ]


@router.post("", response_model=ShiftRequiredSkill)
async def create_skill(payload: SkillCreateRequest, current_user: CurrentUser = Depends(require_roles("admin"))) -> ShiftRequiredSkill:
    """Create skill.
    
    Args:
        payload: Validated request payload model.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `ShiftRequiredSkill`.
    """
    skill = await create_skill_record(name=payload.name, actor_id=current_user.id)
    return ShiftRequiredSkill(id=skill.id, name=skill.name)


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, current_user: CurrentUser = Depends(require_roles("admin"))) -> dict[str, bool]:
    """Delete skill.
    
    Args:
        skill_id: Identifier for the target resource.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        True when the operation succeeds, otherwise False.
    """
    await delete_skill_record(skill_id=skill_id, actor_id=current_user.id)
    return {"deleted": True}
