"""
MODULE: /apps/api/app/modules/notifications/service.py

FUNCTION:
    Implements notifications domain workflows for listing, read state, and preferences.

DEPENDENCIES:
    - /apps/api/app/modules/notifications/router.py
    - /apps/api/app/modules/notifications/__init__.py

IMPORTANCE:
    Centralizing notification logic here preserves consistent behavior and keeps route
    orchestration minimal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.modules.notifications.exceptions import (
    InvalidNotificationPreferenceError,
    NotificationNotFoundError,
    NotificationUserNotFoundError,
)
from app.modules.notifications.repository import NotificationsRepository, get_notifications_repository
from app.services.notifications import to_notification_response

VALID_NOTIFICATION_PREFERENCES = {"in_app", "in_app_email"}


# PATTERN: Transaction Script
# Service functions orchestrate repository calls and shape stable response payloads.
async def list_notifications(
    *,
    user_id: str,
    page: int,
    limit: int,
    unread_only: bool,
    repository: NotificationsRepository | None = None,
) -> dict[str, Any]:
    """Return paginated notifications and unread totals for a user."""

    repo = repository or get_notifications_repository()
    where: dict[str, Any] = {"user_id": user_id}
    if unread_only:
        where["read_at"] = None

    skip = (page - 1) * limit
    records = await repo.list_notifications(where=where, skip=skip, take=limit)
    total = await repo.count_notifications(where=where)
    unread_count = await repo.count_notifications(where={"user_id": user_id, "read_at": None})

    return {
        "unread_count": unread_count,
        "notifications": [to_notification_response(item) for item in records],
        "pagination": {"page": page, "limit": limit, "total": total},
    }


async def mark_all_read(
    *,
    user_id: str,
    repository: NotificationsRepository | None = None,
) -> None:
    """Mark all unread notifications as read for a user."""

    repo = repository or get_notifications_repository()
    await repo.mark_all_read(user_id=user_id, read_at=datetime.now(tz=timezone.utc))


async def mark_notification_read(
    *,
    notification_id: str,
    user_id: str,
    repository: NotificationsRepository | None = None,
) -> None:
    """Mark one notification as read when it belongs to the user."""

    repo = repository or get_notifications_repository()
    notification = await repo.find_notification(notification_id)
    if notification is None or notification.user_id != user_id:
        raise NotificationNotFoundError("Notification not found.")

    if notification.read_at is None:
        await repo.mark_notification_read(
            notification_id=notification_id,
            read_at=datetime.now(tz=timezone.utc),
        )


async def get_preferences(
    *,
    user_id: str,
    repository: NotificationsRepository | None = None,
) -> str:
    """Return the current notification preference for a user."""

    repo = repository or get_notifications_repository()
    user = await repo.find_user(user_id)
    if user is None:
        raise NotificationUserNotFoundError("User not found.")
    return user.notification_pref


async def update_preferences(
    *,
    user_id: str,
    notification_pref: str,
    repository: NotificationsRepository | None = None,
) -> str:
    """Update and return a user's notification preference."""

    if notification_pref not in VALID_NOTIFICATION_PREFERENCES:
        raise InvalidNotificationPreferenceError("Invalid notification preference.")

    repo = repository or get_notifications_repository()
    user = await repo.update_user_notification_preference(
        user_id=user_id,
        notification_pref=notification_pref,
    )
    return user.notification_pref

