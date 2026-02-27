from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.routes import assignments


@pytest.mark.asyncio
async def test_weekly_hours_warning_selects_only_weekly_rule() -> None:
    warning = SimpleNamespace(rule="WEEKLY_HOURS", description="Projected weekly hours would be 36.0.")
    warnings = [
        SimpleNamespace(rule="DAILY_HOURS", description="Projected daily hours would be 9.0."),
        warning,
    ]

    selected = assignments._weekly_hours_warning(warnings)

    assert selected is warning


@pytest.mark.asyncio
async def test_create_overtime_warning_notifications_notifies_unique_managers(monkeypatch) -> None:
    create_calls: list[dict] = []

    async def fake_create_notification(**kwargs):
        create_calls.append(kwargs)
        return SimpleNamespace(
            id=f"notif-{kwargs['user_id']}",
            user_id=kwargs["user_id"],
            type=kwargs["notif_type"],
            message=kwargs["message"],
        )

    monkeypatch.setattr(assignments, "create_notification", fake_create_notification)

    tx = SimpleNamespace(
        managerlocationassignment=SimpleNamespace(
            find_many=AsyncMock(
                return_value=[
                    SimpleNamespace(manager_id="manager-2"),
                    SimpleNamespace(manager_id="manager-1"),
                    SimpleNamespace(manager_id="manager-2"),
                ]
            )
        )
    )

    notifications = await assignments._create_overtime_warning_notifications(
        tx=tx,
        location_id="loc-1",
        assigned_user=SimpleNamespace(id="staff-1", name="Maria"),
        shift_id="shift-1",
        projected_weekly_hours=36.25,
        warning_description="Projected weekly hours would be 36.25.",
    )

    assert [item.user_id for item in notifications] == ["manager-1", "manager-2"]
    assert len(create_calls) == 2
    assert all(call["notif_type"] == "overtime.warning" for call in create_calls)
    assert all(call["payload"]["projectedWeeklyHours"] == 36.25 for call in create_calls)
