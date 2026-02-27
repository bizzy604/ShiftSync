"""
MODULE: /apps/api/app/modules/skills/schemas.py

FUNCTION:
    Defines request payload models for the skills domain module.

DEPENDENCIES:
    - /apps/api/app/modules/skills/router.py

IMPORTANCE:
    Keeping module-local schemas near route and service logic improves discoverability
    and reduces accidental cross-domain coupling.
"""

from pydantic import BaseModel, Field


class SkillCreateRequest(BaseModel):
    """Request payload for creating a catalog skill."""

    name: str = Field(min_length=1, max_length=100)
