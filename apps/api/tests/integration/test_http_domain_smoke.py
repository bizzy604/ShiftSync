"""
MODULE: /apps/api/tests/integration/test_http_domain_smoke.py

FUNCTION:
    Provides route-level HTTP and websocket smoke checks for every API domain using an
    in-process FastAPI app with lightweight runtime state stubs.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/tests/integration/test_route_surface.py

IMPORTANCE:
    These checks catch accidental route breakage early by asserting each domain has at
    least one callable endpoint path that returns an expected guard/validation response.
"""

from __future__ import annotations

from typing import Iterable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.router import api_router


class DummySessionStore:
    """Minimal async session-store stub for unauthenticated smoke requests."""

    async def exists(self, _: str) -> bool:
        return False

    async def touch(self, _: str, __: int) -> None:
        return None


@pytest.fixture()
def smoke_app() -> FastAPI:
    """Build a lightweight in-process app for route smoke checks."""

    app = FastAPI()
    app.include_router(api_router)
    app.state.session_store = DummySessionStore()
    app.state.ws_manager = None
    return app


@pytest.fixture()
def client(smoke_app: FastAPI) -> Iterable[TestClient]:
    """Yield a synchronous test client for in-process HTTP requests."""

    with TestClient(smoke_app) as test_client:
        yield test_client


DOMAIN_ROUTE_SMOKE_CASES: list[tuple[str, str, str, set[int]]] = [
    ("analytics", "GET", "/api/v1/analytics/overtime-dashboard", {401, 422}),
    ("assignments", "GET", "/api/v1/assignments/me", {401, 422}),
    ("audit", "GET", "/api/v1/audit/audit-logs", {401, 422}),
    ("auth", "POST", "/api/v1/auth/login", {422}),
    ("locations", "GET", "/api/v1/locations", {401, 422}),
    ("notifications", "GET", "/api/v1/notifications", {401, 422}),
    ("shifts", "GET", "/api/v1/shifts", {401, 422}),
    ("skills", "POST", "/api/v1/skills", {401, 422}),
    ("swaps", "GET", "/api/v1/swaps", {401, 422}),
    ("users", "GET", "/api/v1/users", {401, 422}),
]


@pytest.mark.parametrize("domain,method,path,expected_statuses", DOMAIN_ROUTE_SMOKE_CASES)
def test_domain_representative_routes_return_expected_guard_or_validation_status(
    client: TestClient,
    domain: str,
    method: str,
    path: str,
    expected_statuses: set[int],
) -> None:
    """Ensure each domain has at least one routable endpoint under `/api/v1`."""

    response = client.request(method, path)
    assert response.status_code in expected_statuses, (
        f"Unexpected status for {domain} route {method} {path}: {response.status_code}"
    )


def test_realtime_websocket_smoke_requires_auth_token(smoke_app: FastAPI) -> None:
    """Ensure websocket endpoint remains mounted and rejects unauthenticated clients."""

    with TestClient(smoke_app) as test_client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with test_client.websocket_connect("/api/v1/realtime/ws"):
                pass

    assert exc.value.code == 4401


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/v1/auth/login"),
        ("GET", "/api/v1/shifts"),
        ("GET", "/api/v1/swaps"),
        ("GET", "/api/v1/notifications"),
    ],
)
def test_top_workflow_smoke_paths_are_registered(method: str, path: str, client: TestClient) -> None:
    """Smoke-check top workflows required by Phase 8 (auth, scheduling, swaps, notifications)."""

    response = client.request(method, path)
    assert response.status_code in {401, 422}
