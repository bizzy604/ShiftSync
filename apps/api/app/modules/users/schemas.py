"""
MODULE: /apps/api/app/modules/users/schemas.py

FUNCTION:
    Re-exports users request/response schemas for the modular domain boundary.

DEPENDENCIES:
    - /apps/api/app/modules/users/router.py
    - /apps/api/app/modules/users/__init__.py

IMPORTANCE:
    Keeping schema imports local to the module improves discoverability while preserving
    shared API contract definitions.
"""

from app.schemas.user import (
    AvailabilityEntryResponse,
    AvailabilityReplaceRequest,
    AvailabilityResponse,
    CertificationAttachRequest,
    ExceptionAvailabilityIn,
    RecurringAvailabilityIn,
    SkillAttachRequest,
    UserCertificationResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserSkillResponse,
    UserUpdateRequest,
)

__all__ = [
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserResponse",
    "UserListResponse",
    "SkillAttachRequest",
    "UserSkillResponse",
    "CertificationAttachRequest",
    "UserCertificationResponse",
    "RecurringAvailabilityIn",
    "ExceptionAvailabilityIn",
    "AvailabilityReplaceRequest",
    "AvailabilityEntryResponse",
    "AvailabilityResponse",
]

