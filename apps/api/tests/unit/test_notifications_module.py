"""
MODULE: /apps/api/tests/unit/test_notifications_module.py

FUNCTION:
    Covers notifications module repository and service behavior with isolated unit tests.

DEPENDENCIES:
    - /apps/api/app/modules/notifications/repository.py
    - /apps/api/app/modules/notifications/service.py

IMPORTANCE:
    These tests guard preference validation and ownership checks introduced in the modular
    notifications service layer.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.notifications.exceptions import (
    InvalidNotificationPreferenceError,
    NotificationNotFoundError,
)
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.service import mark_notification_read, update_preferences


@pytest.mark.asyncio
async def test_notifications_repository_marks_all_unread_as_read() -> None:
    fake_db = SimpleNamespace(notification=SimpleNamespace(update_many=AsyncMock(return_value=None)))
    repo = NotificationsRepository(db=fake_db)

    await repo.mark_all_read(user_id="user-1", read_at=datetime(2026, 1, 1))

    fake_db.notification.update_many.assert_awaited_once()
    kwargs = fake_db.notification.update_many.await_args.kwargs
    assert kwargs["where"] == {"user_id": "user-1", "read_at": None}
    assert kwargs["data"]["read_at"] == datetime(2026, 1, 1)


@pytest.mark.asyncio
async def test_update_preferences_rejects_invalid_values() -> None:
    with pytest.raises(InvalidNotificationPreferenceError):
        await update_preferences(
            user_id="user-1",
            notification_pref="sms_only",
            repository=SimpleNamespace(),
        )


@pytest.mark.asyncio
async def test_mark_notification_read_requires_notification_ownership() -> None:
    repo = SimpleNamespace(find_notification=AsyncMock(return_value=None))

    with pytest.raises(NotificationNotFoundError):
        await mark_notification_read(notification_id="notif-1", user_id="user-1", repository=repo)
