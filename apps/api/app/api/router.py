from fastapi import APIRouter

from app.api.routes import analytics, assignments, audit, auth, locations, notifications, realtime, shifts, swaps, users


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(shifts.router, tags=["shifts"])
api_router.include_router(assignments.router, tags=["assignments"])
api_router.include_router(swaps.router, tags=["swaps"])
api_router.include_router(notifications.router, tags=["notifications"])
api_router.include_router(analytics.router, tags=["analytics"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(realtime.router, tags=["realtime"])
