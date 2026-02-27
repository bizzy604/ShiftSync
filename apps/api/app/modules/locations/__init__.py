"""
MODULE: /apps/api/app/modules/locations/__init__.py

FUNCTION:
    Defines the public API boundary and exported contracts for the locations domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/locations/router.py

IMPORTANCE:
    Exporting a stable surface here prevents external callers from importing private
    internals directly.
"""

from app.modules.locations.router import (
    LocationCreateRequest,
    LocationListResponse,
    LocationResponse,
    LocationUpdateRequest,
    create_location,
    get_location,
    list_locations,
    router,
    update_location,
)
from app.modules.locations.service import (
    create_location as create_location_record,
    get_location as get_location_record,
    list_locations as list_locations_record,
    update_location as update_location_record,
)

__all__ = [
    "router",
    "LocationCreateRequest",
    "LocationUpdateRequest",
    "LocationResponse",
    "LocationListResponse",
    "list_locations",
    "create_location",
    "get_location",
    "update_location",
    "list_locations_record",
    "create_location_record",
    "get_location_record",
    "update_location_record",
]
