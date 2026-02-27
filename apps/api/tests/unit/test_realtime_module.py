"""
MODULE: /apps/api/tests/unit/test_realtime_module.py

FUNCTION:
    Covers realtime module repository and websocket service behavior with isolated unit tests.

DEPENDENCIES:
    - /apps/api/app/modules/realtime/repository.py
    - /apps/api/app/modules/realtime/service.py

IMPORTANCE:
    These tests protect websocket authentication/session behavior and manager-location
    subscription wiring introduced by the modular realtime boundary.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocketDisconnect

from app.modules.realtime import repository as realtime_repository
from app.modules.realtime import service as realtime_service


class FakeWebSocket:
    """Small websocket stub for unit-testing realtime service orchestration."""

    def __init__(self, *, token: str | None, app_state: object, messages: list[object] | None = None) -> None:
        self.query_params: dict[str, str] = {}
        if token:
            self.query_params["token"] = token
        self.cookies: dict[str, str] = {}
        self.app = SimpleNamespace(state=app_state)
        self._messages = list(messages or [])
        self.closed_codes: list[int] = []
        self.sent_payloads: list[dict] = []

    async def close(self, code: int) -> None:
        self.closed_codes.append(code)

    async def receive_json(self) -> dict:
        item = self._messages.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def send_json(self, payload: dict) -> None:
        self.sent_payloads.append(payload)


@pytest.mark.asyncio
async def test_realtime_repository_lists_unique_sorted_manager_locations() -> None:
    fake_db = SimpleNamespace(
        managerlocationassignment=SimpleNamespace(
            find_many=AsyncMock(
                return_value=[
                    SimpleNamespace(location_id="loc-2"),
                    SimpleNamespace(location_id="loc-1"),
                    SimpleNamespace(location_id="loc-2"),
                ]
            )
        )
    )

    location_ids = await realtime_repository.list_manager_location_ids(user_id="manager-1", db=fake_db)

    assert location_ids == ["loc-1", "loc-2"]


@pytest.mark.asyncio
async def test_websocket_endpoint_closes_when_token_missing() -> None:
    app_state = SimpleNamespace(
        session_store=SimpleNamespace(exists=AsyncMock(return_value=False)),
        ws_manager=SimpleNamespace(connect=AsyncMock(), disconnect=AsyncMock()),
    )
    websocket = FakeWebSocket(token=None, app_state=app_state)

    await realtime_service.websocket_endpoint(websocket)

    assert websocket.closed_codes == [4401]
    app_state.ws_manager.connect.assert_not_awaited()


@pytest.mark.asyncio
async def test_websocket_endpoint_manager_ping_pong_and_disconnect(monkeypatch) -> None:
    session_store = SimpleNamespace(exists=AsyncMock(return_value=True))
    ws_manager = SimpleNamespace(connect=AsyncMock(), disconnect=AsyncMock())
    app_state = SimpleNamespace(session_store=session_store, ws_manager=ws_manager)
    websocket = FakeWebSocket(
        token="token-1",
        app_state=app_state,
        messages=[{"event": "ping"}, WebSocketDisconnect(code=1000)],
    )

    monkeypatch.setattr(
        realtime_service,
        "decode_access_token",
        lambda _: {"sid": "sid-1", "sub": "manager-1", "role": "manager"},
    )
    monkeypatch.setattr(
        realtime_service,
        "list_manager_location_ids",
        AsyncMock(return_value=["loc-1", "loc-2"]),
    )

    await realtime_service.websocket_endpoint(websocket)

    session_store.exists.assert_awaited_once_with("session:sid-1")
    ws_manager.connect.assert_awaited_once_with(websocket, user_id="manager-1", location_ids=["loc-1", "loc-2"])
    ws_manager.disconnect.assert_awaited_once_with(websocket, user_id="manager-1", location_ids=["loc-1", "loc-2"])
    assert websocket.sent_payloads == [{"event": "pong", "payload": {}}]
