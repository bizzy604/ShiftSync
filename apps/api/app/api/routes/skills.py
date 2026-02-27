from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, require_roles
from app.core.database import prisma
from app.schemas.shift import ShiftRequiredSkill
from app.services.audit import create_audit_log

router = APIRouter()


class SkillCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@router.get("", response_model=list[ShiftRequiredSkill])
async def list_skills() -> list[ShiftRequiredSkill]:
    skills = await prisma.skill.find_many(order={"name": "asc"})
    return [
        ShiftRequiredSkill(
            id=skill.id,
            name=skill.name,
        )
        for skill in skills
    ]


@router.post("", response_model=ShiftRequiredSkill)
async def create_skill(payload: SkillCreateRequest, current_user: CurrentUser = Depends(require_roles("admin"))) -> ShiftRequiredSkill:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Skill name cannot be empty.")

    existing_skills = await prisma.skill.find_many()
    if any(item.name.lower() == name.lower() for item in existing_skills):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Skill already exists.")

    async with prisma.tx() as tx:
        skill = await tx.skill.create(data={"name": name})
        await create_audit_log(
            actor_id=current_user.id,
            action_type="skill.catalog.add",
            entity_type="skill",
            entity_id=skill.id,
            after_state={"name": skill.name},
            db=tx,
        )
    return ShiftRequiredSkill(id=skill.id, name=skill.name)


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, current_user: CurrentUser = Depends(require_roles("admin"))) -> dict[str, bool]:
    skill = await prisma.skill.find_unique(where={"id": skill_id})
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found.")

    user_links = await prisma.userskill.count(where={"skill_id": skill_id})
    shift_links = await prisma.shift.count(where={"required_skill_id": skill_id})
    if user_links > 0 or shift_links > 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Skill is in use and cannot be deleted.",
        )

    async with prisma.tx() as tx:
        await tx.skill.delete(where={"id": skill_id})
        await create_audit_log(
            actor_id=current_user.id,
            action_type="skill.catalog.remove",
            entity_type="skill",
            entity_id=skill_id,
            before_state={"name": skill.name},
            db=tx,
        )
    return {"deleted": True}
