"""
MODULE: /apps/api/tests/integration/test_deps_manager_scope.py

FUNCTION:
    Contains integration tests covering `test_deps_manager_scope` API and workflow behavior.

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

from app.api import deps

shared_auth_deps = importlib.import_module("app.shared.dependencies.auth")


@pytest.mark.asyncio
async def test_get_current_user_uses_live_manager_location_assignments(monkeypatch) -> None:
    fake_settings = SimpleNamespace(token_cookie_name="access_token", access_token_expire_minutes=120)
    fake_payload = {
        "sid": "sid-1",
        "sub": "manager-1",
        "role": "manager",
        "location_ids": ["stale-location"],
    }

    fake_session_store = SimpleNamespace(
        exists=AsyncMock(return_value=True),
        touch=AsyncMock(return_value=True),
    )
    fake_prisma = SimpleNamespace(
        managerlocationassignment=SimpleNamespace(
            find_many=AsyncMock(
                return_value=[
                    SimpleNamespace(location_id="loc-b"),
                    SimpleNamespace(location_id="loc-a"),
                    SimpleNamespace(location_id="loc-b"),
                ]
            )
        )
    )
    fake_request = SimpleNamespace(cookies={"access_token": "token"})

    monkeypatch.setattr(shared_auth_deps, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(shared_auth_deps, "decode_access_token", lambda token: fake_payload)
    monkeypatch.setattr(shared_auth_deps, "prisma", fake_prisma)

    current = await deps.get_current_user(request=fake_request, session_store=fake_session_store)

    assert current.id == "manager-1"
    assert current.role == "manager"
    assert current.location_ids == ["loc-a", "loc-b"]
    fake_session_store.exists.assert_awaited_once_with("session:sid-1")
    fake_session_store.touch.assert_awaited_once_with("session:sid-1", 120 * 60)
    fake_prisma.managerlocationassignment.find_many.assert_awaited_once_with(where={"manager_id": "manager-1"})
