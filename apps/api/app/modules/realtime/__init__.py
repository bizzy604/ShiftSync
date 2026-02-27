"""
MODULE: /apps/api/app/modules/realtime/__init__.py

FUNCTION:
    Defines the public API boundary and exported contracts for the realtime domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/realtime/router.py

IMPORTANCE:
    A stable public boundary keeps websocket consumers decoupled from internal refactors
    in realtime service/repository layers.
"""

from app.modules.realtime.repository import list_manager_location_ids
from app.modules.realtime.router import router, websocket_endpoint

__all__ = ["router", "websocket_endpoint", "list_manager_location_ids"]
