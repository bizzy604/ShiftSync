from fastapi import APIRouter

from app.core.database import prisma
from app.schemas.shift import ShiftRequiredSkill

router = APIRouter()

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
