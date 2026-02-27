"""
MODULE: /apps/api/app/modules/realtime/router.py

FUNCTION:
    Registers realtime websocket routes while delegating protocol behavior to service.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/realtime/router.py
    - /apps/api/app/modules/realtime/__init__.py

IMPORTANCE:
    Keeping route registration thin ensures websocket contracts remain stable while
    authentication/session logic evolves in the service layer.
"""

from fastapi import APIRouter

from app.modules.realtime.service import websocket_endpoint


router = APIRouter()
router.add_api_websocket_route("/ws", websocket_endpoint)

__all__ = ["router", "websocket_endpoint"]
