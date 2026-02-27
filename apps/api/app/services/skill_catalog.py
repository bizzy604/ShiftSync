"""
MODULE: /apps/api/app/services/skill_catalog.py

FUNCTION:
    Provides a compatibility service facade that forwards to the modular skills domain service.

DEPENDENCIES:
    - /apps/api/tests/integration/test_skills_routes.py

IMPORTANCE:
    This bridge preserves legacy import paths while the modular-monolith migration is completed
    incrementally.
"""

from app.modules.skills.service import create_skill, delete_skill, list_skills

__all__ = ["list_skills", "create_skill", "delete_skill"]
