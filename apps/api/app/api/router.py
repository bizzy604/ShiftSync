"""
MODULE: /apps/api/app/api/router.py

FUNCTION:
    Registers all API routers and composes the public `/api/v1` surface.

DEPENDENCIES:
    - /apps/api/app/main.py
    - /apps/api/tests/integration/test_route_surface.py

IMPORTANCE:
    This module is important for maintainability and predictable behavior of `router`.
"""

from fastapi import APIRouter

from app.modules import analytics as analytics_module
from app.modules import assignments as assignments_module
from app.modules import auth as auth_module
from app.modules import audit as audit_module
from app.modules import locations as locations_module
from app.modules import notifications as notifications_module
from app.modules import realtime as realtime_module
from app.modules import shifts as shifts_module
from app.modules import skills as skills_module
from app.modules import swaps as swaps_module
from app.modules import users as users_module


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_module.router, prefix="/auth", tags=["auth"])
api_router.include_router(users_module.router, prefix="/users", tags=["users"])
api_router.include_router(locations_module.router, prefix="/locations", tags=["locations"])
api_router.include_router(shifts_module.router, prefix="/shifts", tags=["shifts"])
api_router.include_router(assignments_module.router, prefix="/assignments", tags=["assignments"])
api_router.include_router(swaps_module.router, prefix="/swaps", tags=["swaps"])
api_router.include_router(notifications_module.router, tags=["notifications"])
api_router.include_router(analytics_module.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(audit_module.router, prefix="/audit", tags=["audit"])
api_router.include_router(realtime_module.router, prefix="/realtime", tags=["realtime"])
api_router.include_router(skills_module.router, prefix="/skills", tags=["skills"])
