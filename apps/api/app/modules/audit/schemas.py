"""
MODULE: /apps/api/app/modules/audit/schemas.py

FUNCTION:
    Re-exports audit request/response schemas for the modular domain boundary.

DEPENDENCIES:
    - /apps/api/app/modules/audit/router.py
    - /apps/api/app/modules/audit/__init__.py

IMPORTANCE:
    Keeping schema imports local to the module improves discoverability while preserving
    existing shared API contracts.
"""

from app.schemas.audit import AuditLogListResponse, AuditLogResponse

__all__ = [
    "AuditLogResponse",
    "AuditLogListResponse",
]

