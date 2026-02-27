"""
MODULE: /apps/api/app/schemas/notification.py

FUNCTION:
    Defines Pydantic API contract models for `notification` requests and responses.

DEPENDENCIES:
    - /apps/api/app/modules/notifications/router.py

IMPORTANCE:
    This module defines API contracts that protect type safety and compatibility between
    backend and frontend.
"""

from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """NotificationResponse response model."""
    id: str
    type: str
    message: str
    payload: dict
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    """NotificationListResponse response model."""
    unread_count: int
    notifications: list[NotificationResponse]
    pagination: dict[str, int]


class NotificationPreferencesResponse(BaseModel):
    """NotificationPreferencesResponse response model."""
    notification_pref: str


class NotificationPreferencesUpdateRequest(BaseModel):
    """NotificationPreferencesUpdateRequest request model."""
    notification_pref: str
