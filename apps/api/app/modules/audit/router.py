"""
MODULE: /apps/api/app/modules/audit/router.py

FUNCTION:
    Exposes audit HTTP endpoints through a thin modular route layer.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/audit/router.py

IMPORTANCE:
    This route layer preserves existing audit API contracts while delegating query logic
    to service and repository layers.
"""

import csv
import io
import json
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, require_roles
from app.modules.audit.service import export_audit_logs as export_audit_logs_records
from app.modules.audit.service import list_audit_logs as list_audit_logs_records
from app.schemas.audit import AuditLogListResponse


router = APIRouter()


def _csv_row_state(value: Any) -> str:
    """Serialize state dictionaries for CSV output."""

    return json.dumps(value) if value is not None else ""


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
    """Return paginated audit-log entries."""

    return await list_audit_logs_records(
        current_user=current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit,
    )


async def export_audit_logs(
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    location_id: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> StreamingResponse:
    """Stream audit-log CSV export for administrators."""

    filename, items = await export_audit_logs_records(
        current_user=current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
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
                    _csv_row_state(item.before_state),
                    _csv_row_state(item.after_state),
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(_iter_csv(), media_type="text/csv", headers=headers)


router.add_api_route("/audit-logs", list_audit_logs, methods=["GET"], response_model=AuditLogListResponse)
router.add_api_route("/audit-logs/export", export_audit_logs, methods=["GET"])
