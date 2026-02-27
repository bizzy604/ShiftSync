"""
MODULE: /apps/api/app/modules/skills/dependencies.py

FUNCTION:
    Provides dependency factories for skills domain components.

DEPENDENCIES:
    - /apps/api/app/modules/skills/service.py

IMPORTANCE:
    Centralized factories make it easier to swap repository implementations in tests
    and future runtime wiring.
"""

from app.modules.skills.repository import SkillsRepository, get_skills_repository


def get_skills_repo() -> SkillsRepository:
    """Return the default skills repository dependency."""

    return get_skills_repository()
