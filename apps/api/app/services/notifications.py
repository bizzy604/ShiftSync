from typing import Any

from app.core.database import prisma


async def create_notification(
    *,
    user_id: str,
    notif_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
    db: Any = None,
    ws_manager: Any = None,
) -> object:
    safe_payload = payload or {}
    client = db or prisma
    record = await client.notification.create(
        data={
            "user_id": user_id,
            "type": notif_type,
            "message": message,
            "payload": safe_payload,
        }
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
    payload = record.payload if isinstance(record.payload, dict) else {}
    return {
        "id": record.id,
        "type": record.type,
        "message": record.message,
        "payload": payload,
        "created_at": record.created_at,
        "read_at": record.read_at,
    }
