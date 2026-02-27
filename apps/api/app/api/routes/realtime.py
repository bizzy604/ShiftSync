"""
MODULE: /apps/api/app/api/routes/realtime.py

FUNCTION:
    Defines FastAPI endpoints and request/response orchestration for the `realtime` domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py

IMPORTANCE:
    This module directly shapes externally visible API behavior and role-based access flows.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.database import prisma
from app.core.security import decode_access_token


router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Websocket endpoint.
    
    Args:
        websocket: Input parameter `websocket` used by this operation.
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
        assignments = await prisma.managerlocationassignment.find_many(where={"manager_id": user_id})
        join_locations = sorted({item.location_id for item in assignments})

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
