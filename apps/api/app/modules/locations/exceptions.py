"""
MODULE: /apps/api/app/modules/locations/exceptions.py

FUNCTION:
    Defines typed domain exceptions for locations workflows.

DEPENDENCIES:
    - /apps/api/app/modules/locations/router.py
    - /apps/api/app/modules/locations/service.py

IMPORTANCE:
    Domain exceptions keep service-layer failure semantics explicit while allowing the route
    layer to map each error to stable HTTP responses.
"""


class LocationNotFoundError(Exception):
    """Raised when a requested location record does not exist."""

    def __init__(self, location_id: str) -> None:
        """Initialize the exception with the missing location identifier."""

        super().__init__(f"Location not found: {location_id}")
        self.location_id = location_id


class LocationAccessDeniedError(Exception):
    """Raised when the current user is not authorized for a location."""

