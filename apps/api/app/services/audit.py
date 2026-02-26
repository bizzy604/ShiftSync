from typing import Any

from prisma import Json

from app.core.database import prisma


async def create_audit_log(
    *,
    actor_id: str,
    action_type: str,
    entity_type: str,
    entity_id: str,
    location_id: str | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    reason: str | None = None,
) -> object:
    data: dict[str, Any] = {
        "actor": {"connect": {"id": actor_id}},
        "action_type": action_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        # prisma-client-py expects explicit JSON values for these nullable JSON columns.
        "before_state": Json(before_state or {}),
        "after_state": Json(after_state or {}),
        "reason": reason,
    }
    if location_id is not None:
        data["location"] = {"connect": {"id": location_id}}
    return await prisma.auditlog.create(data=data)
