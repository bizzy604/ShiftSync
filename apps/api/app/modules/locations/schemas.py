"""
MODULE: /apps/api/app/modules/locations/schemas.py

FUNCTION:
    Re-exports locations request/response schemas used by the modular router and services.

DEPENDENCIES:
    - /apps/api/app/modules/locations/router.py
    - /apps/api/app/modules/locations/__init__.py

IMPORTANCE:
    Keeping schema imports module-local preserves discoverability while maintaining the
    existing API contract definitions in `app.schemas.location`.
"""

from app.schemas.location import (
    LocationCreateRequest,
    LocationListResponse,
    LocationResponse,
    LocationUpdateRequest,
)

__all__ = [
    "LocationCreateRequest",
    "LocationUpdateRequest",
    "LocationResponse",
    "LocationListResponse",
]

