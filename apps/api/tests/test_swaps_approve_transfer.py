from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.deps import CurrentUser
from app.api.routes import swaps


class TxContext:
    def __init__(self, tx_client):
        self.tx_client = tx_client

    async def __aenter__(self):
        return self.tx_client

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_approve_transfer_swap_updates_both_assignments_atomically(monkeypatch) -> None:
    future_start = datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc)
    future_end = datetime(2030, 1, 1, 14, 0, tzinfo=timezone.utc)
    location = SimpleNamespace(id="loc-1", name="Ocean Ave", iana_timezone="UTC")
    required_skill = SimpleNamespace(id="skill-1", name="bartender")

    requester_assignment = SimpleNamespace(
        id="assign-a",
        shift_id="shift-a",
        user_id="staff-a",
        status="assigned",
        version=1,
        user=SimpleNamespace(id="staff-a"),
        shift=SimpleNamespace(
            id="shift-a",
            location_id="loc-1",
            required_skill_id="skill-1",
            start_utc=future_start,
            end_utc=future_end,
            location=location,
            required_skill=required_skill,
        ),
    )
    candidate_assignment = SimpleNamespace(
        id="assign-b",
        shift_id="shift-b",
        user_id="staff-b",
        status="assigned",
        version=3,
        user=SimpleNamespace(id="staff-b"),
        shift=SimpleNamespace(
            id="shift-b",
            location_id="loc-1",
            required_skill_id="skill-1",
            start_utc=future_start,
            end_utc=future_end,
            location=location,
            required_skill=required_skill,
        ),
    )
    target_profile = SimpleNamespace(id="staff-b")
    requester_profile = SimpleNamespace(id="staff-a")

    async def fake_find_assignment(*, where, include):
        if where["id"] == "assign-a":
            return requester_assignment
        if where["id"] == "assign-b":
            return candidate_assignment
        return None

    async def fake_find_user(*, where, include):
        if where["id"] == "staff-b":
            return target_profile
        if where["id"] == "staff-a":
            return requester_profile
        return None

    tx_shift_update = AsyncMock()
    tx_swap_update = AsyncMock(
        return_value=SimpleNamespace(
            id="swap-1",
            initiated_by="staff-a",
            target_user_id="staff-b",
            pickup_user_id=None,
            status="APPROVED",
        )
    )
    tx_client = SimpleNamespace(
        shiftassignment=SimpleNamespace(update=tx_shift_update),
        swaprequest=SimpleNamespace(update=tx_swap_update),
    )
    fake_prisma = SimpleNamespace(
        shiftassignment=SimpleNamespace(find_unique=AsyncMock(side_effect=fake_find_assignment)),
        user=SimpleNamespace(find_unique=AsyncMock(side_effect=fake_find_user)),
        tx=lambda: TxContext(tx_client),
    )
    monkeypatch.setattr(swaps, "prisma", fake_prisma)

    monkeypatch.setattr(swaps, "shift_snapshot", lambda shift: shift)
    monkeypatch.setattr(swaps, "user_snapshot", lambda user: user)
    monkeypatch.setattr(swaps, "existing_assignments", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        swaps,
        "evaluate_assignment",
        lambda *args, **kwargs: SimpleNamespace(violations=[], requires_override=False),
    )

    audit_calls: list[dict] = []
    notif_counter = {"value": 0}

    async def fake_audit(**kwargs):
        audit_calls.append(kwargs)

    async def fake_notification(*, user_id: str, notif_type: str, message: str, **kwargs):
        notif_counter["value"] += 1
        return SimpleNamespace(
            id=f"notif-{notif_counter['value']}",
            user_id=user_id,
            type=notif_type,
            message=message,
        )

    monkeypatch.setattr(swaps, "create_audit_log", fake_audit)
    monkeypatch.setattr(swaps, "create_notification", fake_notification)

    ws_manager = SimpleNamespace(
        emit_to_users=AsyncMock(),
        emit_to_user=AsyncMock(),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ws_manager=ws_manager)))

    row = SimpleNamespace(
        id="swap-1",
        requester_assignment_id="assign-a",
        candidate_assignment_id="assign-b",
        target_user_id="staff-b",
        pickup_user_id=None,
        initiated_by="staff-a",
        version=5,
    )
    actor = CurrentUser(id="manager-1", role="manager", location_ids=["loc-1"])

    updated_row, notifications, location_id = await swaps.approve_transfer(
        row=row,
        actor=actor,
        note="Approved for coverage",
        request=request,
        drop=False,
    )

    assert updated_row.status == "APPROVED"
    assert location_id == "loc-1"
    assert len(notifications) == 2
    assert tx_shift_update.await_count == 2
    first_update = tx_shift_update.await_args_list[0].kwargs["data"]
    second_update = tx_shift_update.await_args_list[1].kwargs["data"]
    assert first_update["user_id"] == "staff-b"
    assert second_update["user_id"] == "staff-a"
    assert len(audit_calls) == 1
    assert audit_calls[0]["action_type"] == "swap.approve"
    assert len(audit_calls[0]["after_state"]["transfers"]) == 2
    ws_manager.emit_to_users.assert_awaited_once()
    assignment_events = [
        call for call in ws_manager.emit_to_user.await_args_list if call.args[1] == "assignment.changed"
    ]
    assert len(assignment_events) == 4


@pytest.mark.asyncio
async def test_approve_transfer_legacy_swap_without_candidate_still_approves(monkeypatch) -> None:
    future_start = datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc)
    future_end = datetime(2030, 1, 1, 14, 0, tzinfo=timezone.utc)
    location = SimpleNamespace(id="loc-1", name="Ocean Ave", iana_timezone="UTC")
    required_skill = SimpleNamespace(id="skill-1", name="bartender")

    requester_assignment = SimpleNamespace(
        id="assign-a",
        shift_id="shift-a",
        user_id="staff-a",
        status="swap_pending",
        version=2,
        user=SimpleNamespace(id="staff-a"),
        shift=SimpleNamespace(
            id="shift-a",
            location_id="loc-1",
            required_skill_id="skill-1",
            start_utc=future_start,
            end_utc=future_end,
            location=location,
            required_skill=required_skill,
        ),
    )
    target_profile = SimpleNamespace(id="staff-b")

    async def fake_find_assignment(*, where, include):
        if where["id"] == "assign-a":
            return requester_assignment
        return None

    async def fake_find_user(*, where, include):
        if where["id"] == "staff-b":
            return target_profile
        return None

    tx_shift_update = AsyncMock()
    tx_swap_update = AsyncMock(
        return_value=SimpleNamespace(
            id="swap-legacy-1",
            initiated_by="staff-a",
            target_user_id="staff-b",
            pickup_user_id=None,
            status="APPROVED",
        )
    )
    tx_client = SimpleNamespace(
        shiftassignment=SimpleNamespace(update=tx_shift_update),
        swaprequest=SimpleNamespace(update=tx_swap_update),
    )
    fake_prisma = SimpleNamespace(
        shiftassignment=SimpleNamespace(find_unique=AsyncMock(side_effect=fake_find_assignment)),
        user=SimpleNamespace(find_unique=AsyncMock(side_effect=fake_find_user)),
        tx=lambda: TxContext(tx_client),
    )
    monkeypatch.setattr(swaps, "prisma", fake_prisma)

    monkeypatch.setattr(swaps, "shift_snapshot", lambda shift: shift)
    monkeypatch.setattr(swaps, "user_snapshot", lambda user: user)
    monkeypatch.setattr(swaps, "existing_assignments", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        swaps,
        "evaluate_assignment",
        lambda *args, **kwargs: SimpleNamespace(violations=[], requires_override=False),
    )

    audit_calls: list[dict] = []

    async def fake_audit(**kwargs):
        audit_calls.append(kwargs)

    async def fake_notification(*, user_id: str, notif_type: str, message: str, **kwargs):
        return SimpleNamespace(id=f"notif-{user_id}", user_id=user_id, type=notif_type, message=message)

    monkeypatch.setattr(swaps, "create_audit_log", fake_audit)
    monkeypatch.setattr(swaps, "create_notification", fake_notification)

    ws_manager = SimpleNamespace(
        emit_to_users=AsyncMock(),
        emit_to_user=AsyncMock(),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ws_manager=ws_manager)))

    row = SimpleNamespace(
        id="swap-legacy-1",
        requester_assignment_id="assign-a",
        candidate_assignment_id=None,
        target_user_id="staff-b",
        pickup_user_id=None,
        initiated_by="staff-a",
        version=4,
    )
    actor = CurrentUser(id="manager-1", role="manager", location_ids=["loc-1"])

    updated_row, notifications, _ = await swaps.approve_transfer(
        row=row,
        actor=actor,
        note="Approved legacy swap",
        request=request,
        drop=False,
    )

    assert updated_row.status == "APPROVED"
    assert len(notifications) == 2
    assert tx_shift_update.await_count == 1
    assert tx_shift_update.await_args_list[0].kwargs["data"]["status"] == "assigned"
    assert audit_calls[0]["after_state"]["legacy_single_transfer"] is True
