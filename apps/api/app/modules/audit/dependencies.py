"""
MODULE: /apps/api/app/modules/audit/dependencies.py

FUNCTION:
    Provides FastAPI dependency helpers for wiring audit repositories.

DEPENDENCIES:
    - /apps/api/app/modules/audit/router.py

IMPORTANCE:
    Dependency factories keep repository construction explicit and easy to override in tests.
"""

from app.modules.audit.repository import AuditRepository, get_audit_repository


def get_audit_repo() -> AuditRepository:
    """Return a repository instance for route-level dependency injection."""

    return get_audit_repository()

