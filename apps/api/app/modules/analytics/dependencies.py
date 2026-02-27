"""
MODULE: /apps/api/app/modules/analytics/dependencies.py

FUNCTION:
    Provides FastAPI dependency helpers for wiring analytics repositories.

DEPENDENCIES:
    - /apps/api/app/modules/analytics/router.py

IMPORTANCE:
    Dependency factories keep repository construction explicit and easy to override in tests.
"""

from app.modules.analytics.repository import AnalyticsRepository, get_analytics_repository


def get_analytics_repo() -> AnalyticsRepository:
    """Return a repository instance for route-level dependency injection."""

    return get_analytics_repository()

