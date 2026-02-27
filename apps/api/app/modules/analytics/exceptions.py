"""
MODULE: /apps/api/app/modules/analytics/exceptions.py

FUNCTION:
    Defines typed domain exceptions for analytics workflows.

DEPENDENCIES:
    - /apps/api/app/modules/analytics/router.py
    - /apps/api/app/modules/analytics/service.py

IMPORTANCE:
    Typed exceptions keep validation and lookup failures explicit and stable across
    service and route layers.
"""


class AnalyticsLocationNotFoundError(Exception):
    """Raised when an analytics request references an unknown location."""

    def __init__(self, location_id: str) -> None:
        """Initialize the exception with the missing location identifier."""

        super().__init__(f"Location not found: {location_id}")
        self.location_id = location_id


class AnalyticsValidationError(Exception):
    """Raised when analytics input ranges are invalid."""

