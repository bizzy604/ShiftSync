"""
MODULE: /apps/api/app/modules/notifications/schemas.py

FUNCTION:
    Re-exports notifications request/response schemas for the modular domain boundary.

DEPENDENCIES:
    - /apps/api/app/modules/notifications/router.py
    - /apps/api/app/modules/notifications/__init__.py

IMPORTANCE:
    Keeping schema imports local to the module improves discoverability while preserving
    the existing shared contract definitions.
"""

from app.schemas.notification import (
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    NotificationResponse,
)

__all__ = [
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationPreferencesResponse",
    "NotificationPreferencesUpdateRequest",
]

