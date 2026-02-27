from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.deps import CurrentUser
from app.api.routes import users


@pytest.mark.asyncio
async def test_admin_include_inactive_omits_active_filter(monkeypatch) -> None:
    captured_where: dict = {}

    async def fake_find_many(*, where, **kwargs):
        captured_where.update(where)
        return []

    fake_prisma = SimpleNamespace(
        user=SimpleNamespace(
            find_many=AsyncMock(side_effect=fake_find_many),
            count=AsyncMock(return_value=0),
        )
    )
    monkeypatch.setattr(users, "prisma", fake_prisma)

    response = await users.list_users(
        location_id=None,
        skill_id=None,
        include_inactive=True,
        page=1,
        limit=25,
        current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
    )

    assert response.total == 0
    assert "is_active" not in captured_where


@pytest.mark.asyncio
async def test_manager_include_inactive_is_still_limited_to_active(monkeypatch) -> None:
    captured_where: dict = {}

    async def fake_find_many(*, where, **kwargs):
        captured_where.update(where)
        return []

    fake_prisma = SimpleNamespace(
        user=SimpleNamespace(
            find_many=AsyncMock(side_effect=fake_find_many),
            count=AsyncMock(return_value=0),
        )
    )
    monkeypatch.setattr(users, "prisma", fake_prisma)
    monkeypatch.setattr(users, "get_manager_user_scope", AsyncMock(return_value={"staff-1", "staff-2"}))

    response = await users.list_users(
        location_id=None,
        skill_id=None,
        include_inactive=True,
        page=1,
        limit=25,
        current_user=CurrentUser(id="manager-1", role="manager", location_ids=["loc-1"]),
    )

    assert response.total == 0
    assert captured_where.get("is_active") is True
    assert set(captured_where.get("id", {}).get("in", [])) == {"staff-1", "staff-2"}
