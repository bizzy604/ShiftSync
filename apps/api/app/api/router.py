from fastapi import APIRouter

from app.api.routes import analytics, assignments, audit, auth, locations, notifications, realtime, shifts, swaps, users, skills


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(shifts.router, prefix="/shifts", tags=["shifts"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
api_router.include_router(swaps.router, prefix="/swaps", tags=["swaps"])
api_router.include_router(notifications.router, tags=["notifications"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(realtime.router, prefix="/realtime", tags=["realtime"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
