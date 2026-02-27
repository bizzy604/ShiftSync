"""
MODULE: /apps/api/app/modules/skills/__init__.py

FUNCTION:
    Defines the public API boundary for the skills domain module.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/skills/router.py

IMPORTANCE:
    Exporting a stable public surface here prevents cross-module imports from coupling
    to skills internals.
"""

from app.modules.skills.router import (
    SkillCreateRequest,
    create_skill,
    delete_skill,
    list_skills,
    router,
)
from app.modules.skills.service import (
    create_skill as create_skill_record,
    delete_skill as delete_skill_record,
    list_skills as list_skills_record,
)

__all__ = [
    "router",
    "SkillCreateRequest",
    "list_skills",
    "create_skill",
    "delete_skill",
    "list_skills_record",
    "create_skill_record",
    "delete_skill_record",
]
