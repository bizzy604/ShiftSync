"""
MODULE: /apps/api/app/services/audit.py

FUNCTION:
    Implements reusable domain service logic for `audit` workflows.

DEPENDENCIES:
    - /apps/api/app/api/routes/assignments.py
    - /apps/api/app/api/routes/locations.py
    - /apps/api/app/api/routes/shifts.py
    - /apps/api/app/api/routes/swaps.py
    - /apps/api/app/api/routes/users.py
    - /apps/api/app/services/drop_expiry.py
    - /apps/api/app/services/skill_catalog.py
    - /apps/api/app/services/swap_lifecycle.py

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""

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
    """Create audit log.
    
    Args:
        actor_id: User identifier of the actor performing the operation.
        action_type: Input parameter `action_type` used by this operation.
        entity_type: Input parameter `entity_type` used by this operation.
        entity_id: Identifier for the target resource.
        location_id: Target location identifier.
        before_state: Input parameter `before_state` used by this operation.
        after_state: Input parameter `after_state` used by this operation.
        reason: Reason for the state transition or audit action.
        db: Optional database client override for transaction control/testing.
    
    Returns:
        Result typed as `object`.
    """
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
