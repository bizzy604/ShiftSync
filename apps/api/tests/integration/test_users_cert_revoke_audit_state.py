"""
MODULE: /apps/api/tests/integration/test_users_cert_revoke_audit_state.py

FUNCTION:
    Guards certification revoke audit payload serialization behavior.

DEPENDENCIES:
    - /apps/api/app/modules/users/router.py

IMPORTANCE:
    Prevents regressions where datetime objects leak into JSON audit payloads and
    cause runtime serialization failures.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import importlib

import pytest

from app.api.deps import CurrentUser
from app.modules import users

users_router = importlib.import_module("app.modules.users.router")


class _TxContext:
    def __init__(self, tx_client: object):
        self.tx_client = tx_client

    async def __aenter__(self):
        return self.tx_client

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_remove_user_certification_serializes_revoked_at_in_audit_state(monkeypatch) -> None:
    audit_calls: list[dict] = []

    async def fake_create_audit_log(**kwargs):
        audit_calls.append(kwargs)

    tx_client = SimpleNamespace(
        userlocationcertification=SimpleNamespace(update=AsyncMock(return_value=None)),
        shiftassignment=SimpleNamespace(find_many=AsyncMock(return_value=[])),
        managerlocationassignment=SimpleNamespace(find_many=AsyncMock(return_value=[])),
    )
    fake_prisma = SimpleNamespace(
        userlocationcertification=SimpleNamespace(
            find_unique=AsyncMock(
                return_value=SimpleNamespace(revoked_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
            )
        ),
        location=SimpleNamespace(find_unique=AsyncMock(return_value=SimpleNamespace(id="loc-1", name="Main"))),
        tx=lambda: _TxContext(tx_client),
    )

    monkeypatch.setattr(users_router, "prisma", fake_prisma)
    monkeypatch.setattr(users_router, "create_audit_log", fake_create_audit_log)
    monkeypatch.setattr(users_router, "create_notification", AsyncMock())

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ws_manager=None)))
    response = await users.remove_user_certification(
        user_id="staff-1",
        location_id="loc-1",
        request=request,
        current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
    )

    assert response == {"revoked": True}
    assert len(audit_calls) >= 1
    cert_revoke_audit = next(item for item in audit_calls if item["action_type"] == "cert.revoke")
    assert cert_revoke_audit["before_state"]["revoked_at"] == "2026-01-01T00:00:00+00:00"
