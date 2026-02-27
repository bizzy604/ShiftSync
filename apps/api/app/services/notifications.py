"""
MODULE: /apps/api/app/services/notifications.py

FUNCTION:
    Implements reusable domain service logic for `notifications` workflows.

DEPENDENCIES:
    - /apps/api/app/api/routes/assignments.py
    - /apps/api/app/api/routes/notifications.py
    - /apps/api/app/api/routes/shifts.py
    - /apps/api/app/api/routes/swaps.py
    - /apps/api/app/api/routes/users.py
    - /apps/api/app/services/drop_expiry.py
    - /apps/api/app/services/swap_lifecycle.py

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""

from typing import Any

from app.core.database import prisma
from app.services.contracts import NotificationDataClientProtocol, RealtimeEmitterProtocol
from app.services.email_simulator import should_simulate_email, simulate_email_delivery
from app.services.errors import NotificationTargetNotFoundError


async def create_notification(
    *,
    user_id: str,
    notif_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
    db: NotificationDataClientProtocol | None = None,
    ws_manager: RealtimeEmitterProtocol | None = None,
) -> object:
    # PATTERN: Observer
    # Persist domain event first, then fan out real-time subscriber notifications.
    """Create notification.
    
    Args:
        user_id: Target user identifier.
        notif_type: Input parameter `notif_type` used by this operation.
        message: Input parameter `message` used by this operation.
        payload: Validated request payload model.
        db: Optional database client override for transaction control/testing.
        ws_manager: Optional realtime emitter for websocket fan-out.
    
    Returns:
        Result typed as `object`.
    """
    safe_payload = payload or {}
    client = db or prisma

    user = await client.user.find_unique(where={"id": user_id})
    if user is None:
        raise NotificationTargetNotFoundError(user_id)

    record = await client.notification.create(
        data={
            "user_id": user_id,
            "type": notif_type,
            "message": message,
            "payload": safe_payload,
        }
    )

    if should_simulate_email(getattr(user, "notification_pref", None)):
        simulate_email_delivery(
            user_email=user.email,
            notif_type=notif_type,
            message=message,
            payload=safe_payload,
        )

    if ws_manager is not None:
        await ws_manager.emit_to_user(
            user_id,
            "notification.new",
            {
                "notificationId": record.id,
                "type": record.type,
                "message": record.message,
            },
        )

    return record


def to_notification_response(record: object) -> dict[str, Any]:
    """To notification response.
    
    Args:
        record: Input parameter `record` used by this operation.
    
    Returns:
        Structured dictionary result.
    """
    payload = record.payload if isinstance(record.payload, dict) else {}
    return {
        "id": record.id,
        "type": record.type,
        "message": record.message,
        "payload": payload,
        "created_at": record.created_at,
        "read_at": record.read_at,
    }
