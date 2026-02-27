from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import drop_expiry


class FakeWsManager:
    def __init__(self) -> None:
        self.user_events: list[tuple[list[str], str, dict]] = []
        self.single_events: list[tuple[str, str, dict]] = []

    async def emit_to_users(self, user_ids: list[str], event: str, payload: dict) -> None:
        self.user_events.append((user_ids, event, payload))

    async def emit_to_user(self, user_id: str, event: str, payload: dict) -> None:
        self.single_events.append((user_id, event, payload))


@pytest.mark.asyncio
async def test_expire_drop_request_writes_audit_and_notifications(monkeypatch) -> None:
    audit_calls: list[dict] = []
    notif_calls: list[tuple[str, str]] = []

    async def fake_audit(**kwargs):
        audit_calls.append(kwargs)

    async def fake_notification(*, user_id: str, notif_type: str, message: str, **kwargs):
        notif_calls.append((user_id, message))
        return SimpleNamespace(id=f"notif-{user_id}", user_id=user_id, type=notif_type, message=message)

    monkeypatch.setattr(drop_expiry, "create_audit_log", fake_audit)
    monkeypatch.setattr(drop_expiry, "create_notification", fake_notification)

    now = datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(
        id="drop-1",
        type="drop",
        status="OPEN",
        version=4,
        initiated_by="staff-a",
        pickup_user_id="staff-b",
        requester_assignment=SimpleNamespace(shift=SimpleNamespace(location_id="loc-1")),
    )
    client = SimpleNamespace(
        swaprequest=SimpleNamespace(update=AsyncMock(return_value=SimpleNamespace(status="EXPIRED"))),
        managerlocationassignment=SimpleNamespace(
            find_many=AsyncMock(return_value=[SimpleNamespace(manager_id="manager-1")])
        ),
    )
    ws = FakeWsManager()

    expired = await drop_expiry.expire_drop_request(
        request_row=row,
        now=now,
        db=client,
        ws_manager=ws,
    )

    assert expired is True
    assert client.swaprequest.update.await_count == 1
    assert len(audit_calls) == 1
    assert audit_calls[0]["action_type"] == "drop.expire"
    notified_users = {user_id for user_id, _ in notif_calls}
    assert notified_users == {"staff-a", "staff-b", "manager-1"}
    assert ws.user_events[0][1] == "swap.status_changed"
    assert ws.user_events[0][2]["newStatus"] == "EXPIRED"


@pytest.mark.asyncio
async def test_expire_due_drop_requests_counts_only_expired(monkeypatch) -> None:
    async def fake_audit(**kwargs):
        return None

    async def fake_notification(*, user_id: str, notif_type: str, message: str, **kwargs):
        return SimpleNamespace(id=f"notif-{user_id}", user_id=user_id, type=notif_type, message=message)

    monkeypatch.setattr(drop_expiry, "create_audit_log", fake_audit)
    monkeypatch.setattr(drop_expiry, "create_notification", fake_notification)

    rows = [
        SimpleNamespace(
            id="drop-exp-1",
            type="drop",
            status="OPEN",
            version=1,
            initiated_by="staff-a",
            pickup_user_id=None,
            requester_assignment=SimpleNamespace(shift=SimpleNamespace(location_id="loc-1")),
        ),
        SimpleNamespace(
            id="drop-exp-2",
            type="drop",
            status="PENDING_MANAGER",
            version=2,
            initiated_by="staff-b",
            pickup_user_id="staff-c",
            requester_assignment=SimpleNamespace(shift=SimpleNamespace(location_id="loc-1")),
        ),
    ]
    client = SimpleNamespace(
        swaprequest=SimpleNamespace(
            find_many=AsyncMock(return_value=rows),
            update=AsyncMock(return_value=SimpleNamespace(status="EXPIRED")),
        ),
        managerlocationassignment=SimpleNamespace(find_many=AsyncMock(return_value=[])),
    )

    count = await drop_expiry.expire_due_drop_requests(
        now=datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc),
        db=client,
        ws_manager=None,
    )

    assert count == 2
    assert client.swaprequest.update.await_count == 2
