"""
MODULE: /apps/api/app/modules/audit/service.py

FUNCTION:
    Implements audit-log filtering, transformation, and export preparation workflows.

DEPENDENCIES:
    - /apps/api/app/modules/audit/router.py
    - /apps/api/app/modules/audit/__init__.py

IMPORTANCE:
    Centralizing audit filtering and response shaping keeps route handlers thin and
    preserves consistent query behavior.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from app.api.deps import CurrentUser, ensure_manager_location_access
from app.modules.audit.repository import AuditRepository, get_audit_repository
from app.schemas.audit import AuditLogListResponse, AuditLogResponse


def _range_filter(start_date: date | None, end_date: date | None) -> dict[str, datetime]:
    """Build Prisma-compatible created_at range filters."""

    created: dict[str, datetime] = {}
    if start_date:
        created["gte"] = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    if end_date:
        created["lt"] = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return created


def _state_to_dict(value: Any) -> dict[str, Any] | None:
    """Normalize persisted JSON-state payloads to dictionaries."""

    if isinstance(value, dict):
        return value
    return None


def _to_response(item: object) -> AuditLogResponse:
    """Convert ORM audit-log rows into API response schema."""

    actor_name = item.actor.name if getattr(item, "actor", None) is not None else "unknown"
    return AuditLogResponse(
        id=item.id,
        actor_id=item.actor_id,
        actor_name=actor_name,
        action_type=item.action_type,
        entity_type=item.entity_type,
        entity_id=item.entity_id,
        before_state=_state_to_dict(item.before_state),
        after_state=_state_to_dict(item.after_state),
        reason=item.reason,
        location_id=item.location_id,
        created_at=item.created_at,
    )


def build_where(
    *,
    current_user: CurrentUser,
    entity_type: str | None,
    entity_id: str | None,
    location_id: str | None,
    start_date: date | None,
    end_date: date | None,
) -> dict[str, Any]:
    """Build Prisma filter payload for audit-log list/export requests."""

    where: dict[str, Any] = {}
    if entity_type:
        where["entity_type"] = entity_type
    if entity_id:
        where["entity_id"] = entity_id
    if location_id:
        where["location_id"] = location_id

    created = _range_filter(start_date, end_date)
    if created:
        where["created_at"] = created

    if current_user.role == "manager":
        if location_id:
            ensure_manager_location_access(current_user, location_id)
        else:
            where["location_id"] = {"in": current_user.location_ids}

    return where


# PATTERN: Transaction Script
# Service functions orchestrate repository reads and response shaping.
async def list_audit_logs(
    *,
    current_user: CurrentUser,
    entity_type: str | None,
    entity_id: str | None,
    location_id: str | None,
    start_date: date | None,
    end_date: date | None,
    page: int,
    limit: int,
    repository: AuditRepository | None = None,
) -> AuditLogListResponse:
    """Return paginated audit-log response for list endpoint."""

    repo = repository or get_audit_repository()
    where = build_where(
        current_user=current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
    )
    skip = (page - 1) * limit
    items = await repo.list_audit_logs(where=where, skip=skip, take=limit)
    total = await repo.count_audit_logs(where=where)
    return AuditLogListResponse(
        logs=[_to_response(item) for item in items],
        pagination={"page": page, "limit": limit, "total": total},
    )


async def export_audit_logs(
    *,
    current_user: CurrentUser,
    entity_type: str | None,
    entity_id: str | None,
    location_id: str | None,
    start_date: date | None,
    end_date: date | None,
    repository: AuditRepository | None = None,
) -> tuple[str, list[object]]:
    """Return export filename and audit rows for CSV streaming."""

    repo = repository or get_audit_repository()
    where = build_where(
        current_user=current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
    )
    items = await repo.export_audit_logs(where=where, take=10000)
    filename = "audit_log_export.csv"
    if start_date and end_date:
        filename = f"audit_log_{start_date.isoformat()}_{end_date.isoformat()}.csv"
    return filename, items

