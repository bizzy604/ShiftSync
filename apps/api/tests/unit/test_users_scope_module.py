"""
MODULE: /apps/api/tests/unit/test_users_scope_module.py

FUNCTION:
    Covers users scope/validation service helpers with isolated unit tests.

DEPENDENCIES:
    - /apps/api/app/modules/users/service.py

IMPORTANCE:
    These tests guard manager visibility checks and clock-time validation extracted from
    route handlers during users module migration.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.users.exceptions import UserAccessDeniedError, UserInvalidClockTimeError
from app.modules.users import service as users_service
from app.shared.dependencies import CurrentUser


@pytest.mark.asyncio
async def test_get_manager_user_scope_returns_self_for_non_manager() -> None:
    actor = CurrentUser(id="staff-1", role="staff", location_ids=[])

    result = await users_service.get_manager_user_scope(actor)

    assert result == {"staff-1"}


@pytest.mark.asyncio
async def test_assert_user_visible_denies_non_visible_manager_target(monkeypatch) -> None:
    actor = CurrentUser(id="manager-1", role="manager", location_ids=["loc-1"])
    monkeypatch.setattr(users_service, "get_manager_user_scope", AsyncMock(return_value={"staff-2"}))

    with pytest.raises(UserAccessDeniedError):
        await users_service.assert_user_visible_to_actor(actor, "staff-1")


def test_ensure_clock_rejects_invalid_value() -> None:
    with pytest.raises(UserInvalidClockTimeError):
        users_service.ensure_clock("25:99")
