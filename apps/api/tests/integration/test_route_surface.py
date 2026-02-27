"""
MODULE: /apps/api/tests/integration/test_route_surface.py

FUNCTION:
    Contains integration tests covering `test_route_surface` API and workflow behavior.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module guards against regressions and documents expected behavior for future
    contributors.
"""

from fastapi.routing import APIRoute, APIWebSocketRoute

from app.api.router import api_router

EXPECTED_HTTP_TAGS = {
    "analytics",
    "assignments",
    "audit",
    "auth",
    "locations",
    "notifications",
    "shifts",
    "skills",
    "swaps",
    "users",
}


def _api_routes() -> list[APIRoute]:
    return [route for route in api_router.routes if isinstance(route, APIRoute)]


def test_api_route_count_is_stable() -> None:
    """Keep the published API surface explicit to catch accidental route removals."""
    assert len(_api_routes()) == 62


def test_all_routes_are_under_api_v1_prefix() -> None:
    """Enforce a single versioned API namespace for all HTTP endpoints."""
    for route in _api_routes():
        assert route.path.startswith("/api/v1"), f"Route outside versioned namespace: {route.path}"


def test_route_tags_cover_all_domains() -> None:
    """Ensure each expected domain exposes at least one registered route."""
    discovered: set[str] = set()
    for route in _api_routes():
        for tag in route.tags:
            discovered.add(tag)
    assert EXPECTED_HTTP_TAGS.issubset(discovered)


def test_no_duplicate_method_path_pairs() -> None:
    """Prevent ambiguous route registration for the same method/path pair."""
    seen: set[tuple[str, str]] = set()
    for route in _api_routes():
        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            key = (method, route.path)
            assert key not in seen, f"Duplicate route registration detected: {key}"
            seen.add(key)


def test_realtime_websocket_route_is_registered() -> None:
    """Ensure realtime websocket endpoint remains part of the published API surface."""
    websocket_paths = {
        route.path for route in api_router.routes if isinstance(route, APIWebSocketRoute)
    }
    assert "/api/v1/realtime/ws" in websocket_paths
