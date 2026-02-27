"""
MODULE: /apps/api/app/services/errors.py

FUNCTION:
    Implements reusable domain service logic for `errors` workflows.

DEPENDENCIES:
    - /apps/api/app/services/__init__.py
    - /apps/api/app/services/constraint_engine.py
    - /apps/api/app/services/notifications.py
    - /apps/api/app/services/skill_catalog.py

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""

from __future__ import annotations

from fastapi import status

from app.core.errors import AppError


class ServiceError(AppError):
    """Base typed service-layer error."""


class NotificationTargetNotFoundError(ServiceError):
    """Raised when notification creation targets a missing user."""

    def __init__(self, user_id: str) -> None:
        super().__init__(
            code="NOTIFICATION_TARGET_NOT_FOUND",
            message=f"Cannot create notification for unknown user '{user_id}'.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidAvailabilityWindowError(ServiceError):
    """Raised when an availability rule does not include both clock boundaries."""

    def __init__(self) -> None:
        super().__init__(
            code="INVALID_AVAILABILITY_WINDOW",
            message="Availability windows require start and end clock values.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class SkillNameEmptyError(ServiceError):
    """Raised when creating a skill with an empty normalized name."""

    def __init__(self) -> None:
        super().__init__(
            code="SKILL_NAME_EMPTY",
            message="Skill name cannot be empty.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class SkillAlreadyExistsError(ServiceError):
    """Raised when creating a duplicate skill name."""

    def __init__(self, name: str) -> None:
        super().__init__(
            code="SKILL_EXISTS",
            message=f"Skill '{name}' already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )


class SkillNotFoundError(ServiceError):
    """Raised when deleting a non-existent skill."""

    def __init__(self, skill_id: str) -> None:
        super().__init__(
            code="SKILL_NOT_FOUND",
            message=f"Skill '{skill_id}' not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class SkillInUseError(ServiceError):
    """Raised when deleting a skill that is referenced by users or shifts."""

    def __init__(self) -> None:
        super().__init__(
            code="SKILL_IN_USE",
            message="Skill is in use and cannot be deleted.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
