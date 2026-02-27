"""
MODULE: /apps/api/app/modules/audit/repository.py

FUNCTION:
    Provides persistence operations for audit-log query and export workflows.

DEPENDENCIES:
    - /apps/api/app/modules/audit/service.py

IMPORTANCE:
    Repository isolation keeps audit service logic focused on filtering and transformation
    while hiding storage details.
"""

from __future__ import annotations

from typing import Any

from app.core.database import prisma


class AuditRepository:
    """Repository abstraction for audit-log reads."""

    def __init__(self, db: Any | None = None) -> None:
        """Bind audit queries to a database client or transaction handle."""

        self._db = db or prisma

    async def list_audit_logs(
        self,
        *,
        where: dict[str, Any],
        skip: int,
        take: int,
    ) -> list[object]:
        """Return audit-log rows with actor relation for list endpoints."""

        return await self._db.auditlog.find_many(
            where=where,
            include={"actor": True},
            order={"created_at": "desc"},
            skip=skip,
            take=take,
        )

    async def count_audit_logs(self, *, where: dict[str, Any]) -> int:
        """Return count of audit-log rows matching a filter."""

        return await self._db.auditlog.count(where=where)

    async def export_audit_logs(
        self,
        *,
        where: dict[str, Any],
        take: int = 10000,
    ) -> list[object]:
        """Return audit-log rows with actor relation for export endpoints."""

        return await self._db.auditlog.find_many(
            where=where,
            include={"actor": True},
            order={"created_at": "desc"},
            take=take,
        )


def get_audit_repository(db: Any | None = None) -> AuditRepository:
    """Return a repository instance bound to the provided database context."""

    return AuditRepository(db=db)

