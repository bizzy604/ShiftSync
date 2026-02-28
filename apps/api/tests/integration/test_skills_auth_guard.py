"""
MODULE: /apps/api/tests/integration/test_skills_auth_guard.py

FUNCTION:
    Verifies skills route auth protections in the integrated API router.

DEPENDENCIES:
    - /apps/api/app/api/router.py

IMPORTANCE:
    Prevents regressions that would expose catalog routes without authentication.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import api_router


class DummySessionStore:
    """Minimal async session-store stub for unauthenticated requests."""

    async def exists(self, _: str) -> bool:
        return False

    async def touch(self, _: str, __: int) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(api_router)
    app.state.session_store = DummySessionStore()
    app.state.ws_manager = None
    return app


def test_list_skills_requires_authentication() -> None:
    """GET /skills should require an authenticated user session."""

    with TestClient(_build_app()) as client:
        response = client.get("/api/v1/skills")

    assert response.status_code == 401
