"""
MODULE: /apps/api/app/modules/skills/exceptions.py

FUNCTION:
    Exposes typed exceptions used by the skills domain workflows.

DEPENDENCIES:
    - /apps/api/app/modules/skills/service.py

IMPORTANCE:
    Centralized domain exceptions keep failure semantics explicit and stable across
    route, service, and integration test layers.
"""

from app.services.errors import (
    SkillAlreadyExistsError,
    SkillInUseError,
    SkillNameEmptyError,
    SkillNotFoundError,
)

__all__ = [
    "SkillNameEmptyError",
    "SkillAlreadyExistsError",
    "SkillNotFoundError",
    "SkillInUseError",
]
