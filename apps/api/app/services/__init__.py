"""
MODULE: /apps/api/app/services/__init__.py

FUNCTION:
    Provides package-level exports and initialization for
    `apps/api/app/services/__init__.py`.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""


from app.services.contracts import (
    NotificationDataClientProtocol,
    RealtimeEmitterProtocol,
    SkillCatalogClientProtocol,
)
from app.services.errors import (
    InvalidAvailabilityWindowError,
    NotificationTargetNotFoundError,
    ServiceError,
    SkillAlreadyExistsError,
    SkillInUseError,
    SkillNameEmptyError,
    SkillNotFoundError,
)
from app.services.skill_catalog import create_skill, delete_skill, list_skills

__all__ = [
    "NotificationDataClientProtocol",
    "RealtimeEmitterProtocol",
    "SkillCatalogClientProtocol",
    "ServiceError",
    "NotificationTargetNotFoundError",
    "InvalidAvailabilityWindowError",
    "SkillNameEmptyError",
    "SkillAlreadyExistsError",
    "SkillNotFoundError",
    "SkillInUseError",
    "list_skills",
    "create_skill",
    "delete_skill",
]
