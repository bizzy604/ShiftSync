"""
MODULE: /apps/api/app/modules/notifications/__init__.py

FUNCTION:
    Defines the public API boundary and exported contracts for the notifications domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/notifications/router.py

IMPORTANCE:
    Exporting a stable surface here prevents external callers from importing private
    implementation details directly.
"""

from app.modules.notifications.router import (
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    NotificationResponse,
    get_preferences,
    list_notifications,
    mark_all_read,
    mark_notification_read,
    router,
    update_preferences,
)
from app.modules.notifications.service import (
    get_preferences as get_preferences_record,
    list_notifications as list_notifications_record,
    mark_all_read as mark_all_read_record,
    mark_notification_read as mark_notification_read_record,
    update_preferences as update_preferences_record,
)

__all__ = [
    "router",
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationPreferencesResponse",
    "NotificationPreferencesUpdateRequest",
    "list_notifications",
    "mark_all_read",
    "mark_notification_read",
    "get_preferences",
    "update_preferences",
    "list_notifications_record",
    "mark_all_read_record",
    "mark_notification_read_record",
    "get_preferences_record",
    "update_preferences_record",
]
