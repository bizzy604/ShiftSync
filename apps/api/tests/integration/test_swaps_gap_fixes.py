"""
MODULE: /apps/api/tests/integration/test_swaps_gap_fixes.py

FUNCTION:
    Covers swap/drop behavior introduced by PRD remediation fixes.

DEPENDENCIES:
    - /apps/api/app/modules/swaps/service.py

IMPORTANCE:
    Guards notification persistence, atomic drop pickup, and auto-alert behavior.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.modules.swaps import service as swaps


class _TxContext:
    def __init__(self, tx_client: object):
        self.tx_client = tx_client

    async def __aenter__(self):
        return self.tx_client

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_cancel_swap_persists_notifications_for_participants_and_managers(monkeypatch) -> None:
    created_notifications: list[dict] = []

    async def fake_create_notification(**kwargs):
        created_notifications.append(kwargs)
        return SimpleNamespace(
            id=f"notif-{kwargs['user_id']}",
            user_id=kwargs["user_id"],
            type=kwargs["notif_type"],
            message=kwargs["message"],
        )

    ws_manager = SimpleNamespace(
        emit_to_user=AsyncMock(),
        emit_to_users=AsyncMock(),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ws_manager=ws_manager)))

    base_row = SimpleNamespace(
        id="swap-1",
        type="swap",
        status="PENDING_MANAGER",
        initiated_by="staff-a",
        target_user_id="staff-b",
        pickup_user_id=None,
        version=3,
        requester_assignment=SimpleNamespace(
            shift=SimpleNamespace(location_id="loc-1"),
        ),
    )
    updated_row = SimpleNamespace(
        id="swap-1",
        type="swap",
        status="CANCELLED",
        initiated_by="staff-a",
        target_user_id="staff-b",
        pickup_user_id=None,
        requester_assignment_id="assign-1",
        candidate_assignment_id=None,
        expires_at=None,
        created_at=datetime.now(tz=timezone.utc),
        resolved_at=datetime.now(tz=timezone.utc),
        resolution_note="No longer needed",
        requester_assignment=None,
        target_user=None,
        pickup_user=None,
    )

    tx_client = SimpleNamespace(
        swaprequest=SimpleNamespace(update=AsyncMock(return_value=updated_row)),
    )
    fake_prisma = SimpleNamespace(
        swaprequest=SimpleNamespace(find_unique=AsyncMock(return_value=base_row)),
        managerlocationassignment=SimpleNamespace(
            find_many=AsyncMock(return_value=[SimpleNamespace(manager_id="manager-1")])
        ),
        tx=lambda: _TxContext(tx_client),
    )

    monkeypatch.setattr(swaps, "prisma", fake_prisma)
    monkeypatch.setattr(swaps, "create_notification", fake_create_notification)
    monkeypatch.setattr(swaps, "create_audit_log", AsyncMock())

    await swaps.cancel_swap(
        request_id="swap-1",
        body=swaps.SwapActionRequest(note="No longer needed"),
        request=request,
        current_user=CurrentUser(id="staff-a", role="staff", location_ids=[]),
    )

    notified_users = {item["user_id"] for item in created_notifications}
    assert notified_users == {"staff-a", "staff-b", "manager-1"}
    assert ws_manager.emit_to_users.await_count == 1


@pytest.mark.asyncio
async def test_pickup_drop_returns_conflict_when_atomic_update_loses_race(monkeypatch) -> None:
    shift = SimpleNamespace(
        id="shift-1",
        location_id="loc-1",
        location=SimpleNamespace(name="Main", iana_timezone="UTC"),
        required_skill=SimpleNamespace(name="server"),
        required_skill_id="skill-1",
        start_utc=datetime(2030, 1, 1, 14, 0, tzinfo=timezone.utc),
        end_utc=datetime(2030, 1, 1, 18, 0, tzinfo=timezone.utc),
    )
    row = SimpleNamespace(
        id="drop-1",
        type="drop",
        status="OPEN",
        version=4,
        initiated_by="staff-a",
        requester_assignment=SimpleNamespace(
            id="assign-1",
            user_id="staff-a",
            shift_id="shift-1",
            shift=shift,
        ),
        expires_at=None,
    )
    user = SimpleNamespace(
        id="staff-b",
        name="Morgan",
        home_timezone="UTC",
        user_skills=[],
        user_location_certifications=[],
        availability=[],
        hourly_rate=0,
    )

    tx_client = SimpleNamespace(
        swaprequest=SimpleNamespace(update_many=AsyncMock(return_value={"count": 0})),
    )
    fake_prisma = SimpleNamespace(
        swaprequest=SimpleNamespace(find_unique=AsyncMock(return_value=row)),
        user=SimpleNamespace(find_unique=AsyncMock(return_value=user)),
        tx=lambda: _TxContext(tx_client),
    )

    monkeypatch.setattr(swaps, "prisma", fake_prisma)
    monkeypatch.setattr(swaps, "existing_assignments", AsyncMock(return_value=[]))
    monkeypatch.setattr(swaps, "evaluate_assignment", lambda *_a, **_k: SimpleNamespace(violations=[]))

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ws_manager=None)))

    with pytest.raises(HTTPException) as exc:
        await swaps.pickup_drop(
            request_id="drop-1",
            body=swaps.DropPickupRequest(note=None),
            request=request,
            current_user=CurrentUser(id="staff-b", role="staff", location_ids=[]),
        )

    assert exc.value.status_code == 409
    assert "no longer open" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_create_drop_triggers_automatic_qualified_staff_notification(monkeypatch) -> None:
    shift = SimpleNamespace(
        id="shift-1",
        location_id="loc-1",
        location=SimpleNamespace(name="Main", iana_timezone="UTC"),
        required_skill=SimpleNamespace(name="server"),
        start_utc=datetime(2030, 1, 2, 14, 0, tzinfo=timezone.utc),
    )
    assignment = SimpleNamespace(
        id="assign-1",
        user_id="staff-1",
        status="assigned",
        shift=shift,
    )
    created_row = SimpleNamespace(
        id="drop-1",
        type="drop",
        status="OPEN",
        requester_assignment_id="assign-1",
        target_user_id=None,
        candidate_assignment_id=None,
        pickup_user_id=None,
        initiated_by="staff-1",
        expires_at=shift.start_utc,
        created_at=datetime.now(tz=timezone.utc),
        resolved_at=None,
        resolution_note=None,
        requester_assignment=None,
        target_user=None,
        pickup_user=None,
    )

    tx_client = SimpleNamespace(
        swaprequest=SimpleNamespace(create=AsyncMock(return_value=created_row)),
    )
    fake_prisma = SimpleNamespace(
        swaprequest=SimpleNamespace(count=AsyncMock(return_value=0)),
        shiftassignment=SimpleNamespace(find_unique=AsyncMock(return_value=assignment)),
        tx=lambda: _TxContext(tx_client),
    )

    auto_notify = AsyncMock(return_value=[SimpleNamespace(id="n-1", user_id="staff-2", type="drop.available", message="m")])
    emit_notifications = AsyncMock()

    monkeypatch.setattr(swaps, "prisma", fake_prisma)
    monkeypatch.setattr(swaps, "create_audit_log", AsyncMock())
    monkeypatch.setattr(swaps, "manager_notify", AsyncMock(return_value=[]))
    monkeypatch.setattr(swaps, "_create_drop_available_notifications", auto_notify)
    monkeypatch.setattr(swaps, "emit_notifications", emit_notifications)

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ws_manager=object())))

    await swaps.create_drop(
        payload=swaps.DropCreateRequest(assignment_id="assign-1"),
        request=request,
        current_user=CurrentUser(id="staff-1", role="staff", location_ids=[]),
    )

    auto_notify.assert_awaited_once()
    emit_notifications.assert_awaited_once()
