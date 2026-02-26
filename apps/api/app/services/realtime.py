import asyncio
from collections import defaultdict
from dataclasses import dataclass

from fastapi import WebSocket


@dataclass
class ConnectionContext:
    websocket: WebSocket
    user_id: str
    location_ids: set[str]


class RealtimeManager:
    def __init__(self) -> None:
        self._by_user: dict[str, set[WebSocket]] = defaultdict(set)
        self._by_location: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str, location_ids: list[str]) -> None:
        await websocket.accept()
        async with self._lock:
            self._by_user[user_id].add(websocket)
            for location_id in location_ids:
                self._by_location[location_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: str, location_ids: list[str]) -> None:
        async with self._lock:
            if user_id in self._by_user:
                self._by_user[user_id].discard(websocket)
                if not self._by_user[user_id]:
                    self._by_user.pop(user_id, None)
            for location_id in location_ids:
                if location_id in self._by_location:
                    self._by_location[location_id].discard(websocket)
                    if not self._by_location[location_id]:
                        self._by_location.pop(location_id, None)

    async def emit_to_user(self, user_id: str, event: str, payload: dict) -> None:
        sockets = list(self._by_user.get(user_id, set()))
        await self._broadcast(sockets, event, payload)

    async def emit_to_users(self, user_ids: list[str], event: str, payload: dict) -> None:
        emitted: set[WebSocket] = set()
        sockets: list[WebSocket] = []
        for user_id in user_ids:
            for socket in self._by_user.get(user_id, set()):
                if socket in emitted:
                    continue
                emitted.add(socket)
                sockets.append(socket)
        await self._broadcast(sockets, event, payload)

    async def emit_to_location(self, location_id: str, event: str, payload: dict) -> None:
        sockets = list(self._by_location.get(location_id, set()))
        await self._broadcast(sockets, event, payload)

    async def _broadcast(self, sockets: list[WebSocket], event: str, payload: dict) -> None:
        if not sockets:
            return
        message = {"event": event, "payload": payload}
        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(message)
            except Exception:
                stale.append(socket)

        if stale:
            async with self._lock:
                for socket in stale:
                    for user_id, user_sockets in list(self._by_user.items()):
                        if socket in user_sockets:
                            user_sockets.discard(socket)
                            if not user_sockets:
                                self._by_user.pop(user_id, None)
                    for location_id, location_sockets in list(self._by_location.items()):
                        if socket in location_sockets:
                            location_sockets.discard(socket)
                            if not location_sockets:
                                self._by_location.pop(location_id, None)
