"""
MODULE: /apps/api/app/modules/locations/dependencies.py

FUNCTION:
    Provides FastAPI dependency helpers for wiring locations repositories.

DEPENDENCIES:
    - /apps/api/app/modules/locations/router.py

IMPORTANCE:
    Dependency factories make repository injection explicit and simplify isolated tests.
"""

from app.modules.locations.repository import LocationsRepository, get_locations_repository


def get_locations_repo() -> LocationsRepository:
    """Return a repository instance for route-level dependency injection."""

    return get_locations_repository()

