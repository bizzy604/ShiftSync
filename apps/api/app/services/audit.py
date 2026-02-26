from typing import Any

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
    db: Any = None,
) -> object:
    client = db or prisma
    data: dict[str, Any] = {
        "actor_id": actor_id,
        "action_type": action_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before_state": before_state or {},
        "after_state": after_state or {},
        "reason": reason,
    }
    if location_id is not None:
        data["location_id"] = location_id
    return await client.auditlog.create(data=data)
