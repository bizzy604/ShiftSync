"""
MODULE: /apps/api/tests/integration/test_assignments_notifications.py

FUNCTION:
    Contains integration tests covering `test_assignments_notifications` API and workflow
    behavior.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module guards against regressions and documents expected behavior for future
    contributors.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
import importlib

import pytest

from app.api.deps import CurrentUser
from app.modules import assignments

assignments_service = importlib.import_module("app.modules.assignments.service")


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

    monkeypatch.setattr(assignments_service, "create_notification", fake_create_notification)

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


@pytest.mark.asyncio
async def test_create_assignment_requires_explicit_weekly_overtime_ack(monkeypatch) -> None:
    class _UserLock:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _AssignmentLocks:
        def user_lock(self, _user_id: str):
            return _UserLock()

    shift = SimpleNamespace(
        id="shift-1",
        status="draft",
        headcount_needed=2,
        location_id="loc-1",
        location=SimpleNamespace(name="Main Street"),
    )
    user = SimpleNamespace(
        id="staff-1",
        name="Taylor",
        role="staff",
        is_active=True,
        user_skills=[],
        user_location_certifications=[],
        availability=[],
    )
    weekly_warning = SimpleNamespace(
        rule="WEEKLY_HOURS",
        description="Projected weekly hours would be 36.0 (warning threshold is 35).",
        severity="WARNING",
    )

    fake_prisma = SimpleNamespace(
        user=SimpleNamespace(find_unique=AsyncMock(return_value=user)),
        shiftassignment=SimpleNamespace(
            find_unique=AsyncMock(return_value=None),
            count=AsyncMock(return_value=0),
        ),
    )

    monkeypatch.setattr(assignments_service, "prisma", fake_prisma)
    monkeypatch.setattr(assignments_service, "_get_shift_with_access", AsyncMock(return_value=shift))
    monkeypatch.setattr(assignments_service, "_to_shift_snapshot", lambda _shift: object())
    monkeypatch.setattr(assignments_service, "_to_user_snapshot", lambda _user: object())
    monkeypatch.setattr(assignments_service, "_load_existing_assignments", AsyncMock(return_value=[]))
    monkeypatch.setattr(assignments_service, "_compute_suggestions", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        assignments_service,
        "evaluate_assignment",
        lambda *_args, **_kwargs: SimpleNamespace(
            valid=True,
            violations=[],
            warnings=[weekly_warning],
            requires_override=False,
            projected_weekly_hours=36.0,
            projected_daily_hours=8.0,
            projected_overtime_cost=0.0,
        ),
    )

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                assignment_locks=_AssignmentLocks(),
                ws_manager=None,
            )
        )
    )

    response = await assignments_service.create_assignment(
        payload=assignments.AssignmentCreateRequest(user_id="staff-1"),
        request=request,
        shift_id="shift-1",
        current_user=CurrentUser(id="manager-1", role="manager", location_ids=["loc-1"]),
    )

    assert response.status_code == 422
    payload = response.body.decode("utf-8")
    assert "OVERTIME_ACK_REQUIRED" in payload


