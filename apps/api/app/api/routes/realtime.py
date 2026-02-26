from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.security import decode_access_token


router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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
    location_ids = payload.get("location_ids", [])
    if not isinstance(location_ids, list):
        location_ids = []
    join_locations = location_ids if role == "manager" else []

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
