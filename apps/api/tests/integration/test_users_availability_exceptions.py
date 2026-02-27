"""
MODULE: /apps/api/tests/integration/test_users_availability_exceptions.py

FUNCTION:
    Contains integration tests covering `test_users_availability_exceptions` API and
    workflow behavior.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module guards against regressions and documents expected behavior for future
    contributors.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.deps import CurrentUser
from app.api.routes import users
from app.schemas.user import ExceptionAvailabilityIn


@pytest.mark.asyncio
async def test_replace_availability_writes_exception_specific_date_as_date(monkeypatch) -> None:
    captured_create_rows: list[dict] = []

    async def fake_create_many(*, data):
        captured_create_rows.extend(data)
        return {"count": len(data)}

    tx = SimpleNamespace(
        availability=SimpleNamespace(
            delete_many=AsyncMock(return_value={"count": 0}),
            create_many=AsyncMock(side_effect=fake_create_many),
        ),
        managerlocationassignment=SimpleNamespace(find_many=AsyncMock(return_value=[])),
    )

    class _TxContext:
        async def __aenter__(self):
            return tx

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_prisma = SimpleNamespace(
        user=SimpleNamespace(find_unique=AsyncMock(return_value=SimpleNamespace(id="staff-1", name="Test Staff"))),
        availability=SimpleNamespace(find_many=AsyncMock(return_value=[])),
        userlocationcertification=SimpleNamespace(find_many=AsyncMock(return_value=[])),
        tx=lambda: _TxContext(),
    )

    monkeypatch.setattr(users, "prisma", fake_prisma)
    monkeypatch.setattr(users, "create_audit_log", AsyncMock())
    monkeypatch.setattr(users, "create_notification", AsyncMock())
    monkeypatch.setattr(
        users,
        "get_user_availability",
        AsyncMock(return_value=users.AvailabilityResponse(user_id="staff-1", recurring=[], exceptions=[])),
    )

    payload = users.AvailabilityReplaceRequest(
        recurring=[],
        exceptions=[
            ExceptionAvailabilityIn(
                date=date(2026, 2, 27),
                is_available=True,
                start_clock_time="10:00",
                end_clock_time="14:00",
            )
        ],
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ws_manager=None)))

    await users.replace_user_availability(
        user_id="staff-1",
        payload=payload,
        request=request,
        current_user=CurrentUser(id="staff-1", role="staff", location_ids=[]),
    )

    assert len(captured_create_rows) == 1
    assert captured_create_rows[0]["specific_date"] == date(2026, 2, 27)
    assert type(captured_create_rows[0]["specific_date"]) is date
