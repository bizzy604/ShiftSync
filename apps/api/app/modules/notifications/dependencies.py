"""
MODULE: /apps/api/app/modules/notifications/dependencies.py

FUNCTION:
    Provides FastAPI dependency helpers for wiring notifications repositories.

DEPENDENCIES:
    - /apps/api/app/modules/notifications/router.py

IMPORTANCE:
    Dependency factories keep repository construction explicit and easy to override in tests.
"""

from app.modules.notifications.repository import NotificationsRepository, get_notifications_repository


def get_notifications_repo() -> NotificationsRepository:
    """Return a repository instance for route-level dependency injection."""

    return get_notifications_repository()

