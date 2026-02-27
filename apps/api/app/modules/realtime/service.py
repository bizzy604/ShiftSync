"""
MODULE: /apps/api/app/modules/realtime/service.py

FUNCTION:
    Implements websocket authentication/session validation and realtime channel orchestration.

DEPENDENCIES:
    - /apps/api/app/modules/realtime/router.py
    - /apps/api/app/modules/realtime/__init__.py

IMPORTANCE:
    This service is the realtime gateway for authenticated clients; failures here impact
    all websocket connectivity and live-update delivery across the application.
"""

from __future__ import annotations

from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.modules.realtime.repository import list_manager_location_ids


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle websocket authentication and ping/pong traffic for realtime clients.

    Args:
        websocket: Incoming FastAPI websocket connection.

    Returns:
        None.
    """
    settings = get_settings()
    token = websocket.query_params.get("token") or websocket.cookies.get(settings.token_cookie_name)

    if not token:
        await websocket.close(code=4401)
        return

    try:
        payload = decode_access_token(token)
    except Exception:
        await websocket.close(code=4401)
        return

    sid = payload.get("sid")
    user_id = payload.get("sub")
    if not sid or not user_id:
        await websocket.close(code=4401)
        return

    session_store = websocket.app.state.session_store
    valid_session = await session_store.exists(f"session:{sid}")
    if not valid_session:
        await websocket.close(code=4401)
        return

    role = payload.get("role")
    join_locations: list[str] = []
    if role == "manager":
        join_locations = await list_manager_location_ids(user_id=user_id)

    ws_manager = websocket.app.state.ws_manager
    await ws_manager.connect(websocket, user_id=user_id, location_ids=join_locations)

    try:
        while True:
            message = await websocket.receive_json()
            event = message.get("event")
            if event == "ping":
                await websocket.send_json({"event": "pong", "payload": {}})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id=user_id, location_ids=join_locations)
    except Exception:
        await ws_manager.disconnect(websocket, user_id=user_id, location_ids=join_locations)
