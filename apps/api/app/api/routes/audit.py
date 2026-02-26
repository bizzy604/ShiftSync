import csv
import io
import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, ensure_manager_location_access, require_roles
from app.core.database import prisma
from app.schemas.audit import AuditLogListResponse, AuditLogResponse


router = APIRouter()


def _range_filter(start_date: date | None, end_date: date | None) -> dict[str, datetime]:
    created: dict[str, datetime] = {}
    if start_date:
        created["gte"] = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    if end_date:
        created["lt"] = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return created


def _state_to_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _to_response(item: object) -> AuditLogResponse:
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


def _build_where(
    *,
    current_user: CurrentUser,
    entity_type: str | None,
    entity_id: str | None,
    location_id: str | None,
    start_date: date | None,
    end_date: date | None,
) -> dict[str, Any]:
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


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    location_id: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> AuditLogListResponse:
    where = _build_where(
        current_user=current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
    )
    skip = (page - 1) * limit
    items = await prisma.auditlog.find_many(
        where=where,
        include={"actor": True},
        order={"created_at": "desc"},
        skip=skip,
        take=limit,
    )
    total = await prisma.auditlog.count(where=where)
    return AuditLogListResponse(
        logs=[_to_response(item) for item in items],
        pagination={"page": page, "limit": limit, "total": total},
    )


@router.get("/audit-logs/export")
async def export_audit_logs(
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    location_id: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> StreamingResponse:
    where = _build_where(
        current_user=current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
    )
    items = await prisma.auditlog.find_many(
        where=where,
        include={"actor": True},
        order={"created_at": "desc"},
        take=10000,
    )

    def _iter_csv() -> Any:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "id",
                "actor_id",
                "actor_name",
                "action_type",
                "entity_type",
                "entity_id",
                "location_id",
                "reason",
                "created_at",
                "before_state",
                "after_state",
            ]
        )
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        for item in items:
            actor_name = item.actor.name if item.actor is not None else "unknown"
            writer.writerow(
                [
                    item.id,
                    item.actor_id,
                    actor_name,
                    item.action_type,
                    item.entity_type,
                    item.entity_id,
                    item.location_id or "",
                    item.reason or "",
                    item.created_at.isoformat(),
                    json.dumps(item.before_state) if item.before_state is not None else "",
                    json.dumps(item.after_state) if item.after_state is not None else "",
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    filename = "audit_log_export.csv"
    if start_date and end_date:
        filename = f"audit_log_{start_date.isoformat()}_{end_date.isoformat()}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(_iter_csv(), media_type="text/csv", headers=headers)
