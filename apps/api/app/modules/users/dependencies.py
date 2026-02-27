"""
MODULE: /apps/api/app/modules/users/dependencies.py

FUNCTION:
    Provides FastAPI dependency helpers for wiring users repositories.

DEPENDENCIES:
    - /apps/api/app/modules/users/router.py

IMPORTANCE:
    Dependency factories keep repository construction explicit and easy to override in tests.
"""

from app.modules.users.repository import UsersRepository, get_users_repository


def get_users_repo() -> UsersRepository:
    """Return a repository instance for route-level dependency injection."""

    return get_users_repository()

