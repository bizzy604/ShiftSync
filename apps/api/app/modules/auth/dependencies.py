"""
MODULE: /apps/api/app/modules/auth/dependencies.py

FUNCTION:
    Provides FastAPI dependency helpers for wiring auth repositories.

DEPENDENCIES:
    - /apps/api/app/modules/auth/router.py

IMPORTANCE:
    Dependency factories keep repository construction explicit and easy to override in tests.
"""

from app.modules.auth.repository import AuthRepository, get_auth_repository


def get_auth_repo() -> AuthRepository:
    """Return a repository instance for route-level dependency injection."""

    return get_auth_repository()

