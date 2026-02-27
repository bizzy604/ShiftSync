from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import swap_lifecycle


class FakeWsManager:
    def __init__(self) -> None:
        self.user_events: list[tuple[list[str], str, dict]] = []
        self.single_events: list[tuple[str, str, dict]] = []

    async def emit_to_users(self, user_ids: list[str], event: str, payload: dict) -> None:
        self.user_events.append((user_ids, event, payload))

    async def emit_to_user(self, user_id: str, event: str, payload: dict) -> None:
        self.single_events.append((user_id, event, payload))


@pytest.mark.asyncio
async def test_cancel_rows_updates_status_audits_and_notifies(monkeypatch) -> None:
    audit_calls: list[dict] = []
    notif_calls: list[tuple[str, str, str]] = []

    async def fake_audit(**kwargs):
        audit_calls.append(kwargs)

    async def fake_notification(*, user_id: str, notif_type: str, message: str, **kwargs):
        notif_calls.append((user_id, notif_type, message))
        return SimpleNamespace(id=f"notif-{user_id}", user_id=user_id, type=notif_type, message=message)

    monkeypatch.setattr(swap_lifecycle, "create_audit_log", fake_audit)
    monkeypatch.setattr(swap_lifecycle, "create_notification", fake_notification)

    client = SimpleNamespace(
        swaprequest=SimpleNamespace(update=AsyncMock(return_value=SimpleNamespace(status="CANCELLED"))),
        managerlocationassignment=SimpleNamespace(
            find_many=AsyncMock(return_value=[SimpleNamespace(manager_id="manager-1")])
        ),
    )
    row = SimpleNamespace(
        id="swap-1",
        status="PENDING_MANAGER",
        version=3,
        initiated_by="staff-a",
        target_user_id="staff-b",
        pickup_user_id=None,
        requester_assignment=SimpleNamespace(
            shift_id="shift-1",
            shift=SimpleNamespace(location_id="loc-1"),
        ),
        candidate_assignment=SimpleNamespace(shift_id="shift-2"),
    )
    ws = FakeWsManager()

    count = await swap_lifecycle._cancel_rows(
        client=client,
        rows=[row],
        actor_id="manager-actor",
        reason="Swap cancelled due to shift edit.",
        ws_manager=ws,
    )

    assert count == 1
    assert client.swaprequest.update.await_count == 1
    assert len(audit_calls) == 1
    assert audit_calls[0]["action_type"] == "swap.auto_cancel_shift_edit"
    notified_users = {user_id for user_id, _, _ in notif_calls}
    assert notified_users == {"staff-a", "staff-b", "manager-1"}
    assert ws.user_events[0][1] == "swap.status_changed"
    assert ws.user_events[0][2]["newStatus"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_pending_swaps_for_shift_only_cancels_related_rows(monkeypatch) -> None:
    async def fake_audit(**kwargs):
        return None

    async def fake_notification(*, user_id: str, notif_type: str, message: str, **kwargs):
        return SimpleNamespace(id=f"notif-{user_id}", user_id=user_id, type=notif_type, message=message)

    monkeypatch.setattr(swap_lifecycle, "create_audit_log", fake_audit)
    monkeypatch.setattr(swap_lifecycle, "create_notification", fake_notification)

    row_related = SimpleNamespace(
        id="swap-related",
        status="PENDING_ACCEPTEE",
        version=1,
        initiated_by="staff-a",
        target_user_id="staff-b",
        pickup_user_id=None,
        requester_assignment=SimpleNamespace(
            shift_id="shift-1",
            shift=SimpleNamespace(location_id="loc-1"),
        ),
        candidate_assignment=SimpleNamespace(shift_id="shift-2"),
    )
    row_other = SimpleNamespace(
        id="swap-other",
        status="PENDING_MANAGER",
        version=2,
        initiated_by="staff-c",
        target_user_id="staff-d",
        pickup_user_id=None,
        requester_assignment=SimpleNamespace(
            shift_id="shift-9",
            shift=SimpleNamespace(location_id="loc-9"),
        ),
        candidate_assignment=SimpleNamespace(shift_id="shift-8"),
    )

    update_calls: list[str] = []

    async def fake_update(*, where, data):
        update_calls.append(where["id"])
        return SimpleNamespace(status=data["status"])

    client = SimpleNamespace(
        swaprequest=SimpleNamespace(
            find_many=AsyncMock(return_value=[row_related, row_other]),
            update=AsyncMock(side_effect=fake_update),
        ),
        managerlocationassignment=SimpleNamespace(find_many=AsyncMock(return_value=[])),
    )

    count = await swap_lifecycle.cancel_pending_swaps_for_shift(
        shift_id="shift-1",
        actor_id="manager-actor",
        reason="Swap cancelled due to shift cancellation.",
        ws_manager=None,
        db=client,
    )

    assert count == 1
    assert update_calls == ["swap-related"]
