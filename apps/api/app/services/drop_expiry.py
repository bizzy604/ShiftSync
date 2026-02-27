from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.database import prisma
from app.services.audit import create_audit_log
from app.services.notifications import create_notification


EXPIRABLE_DROP_STATUSES = {"OPEN", "PENDING_MANAGER"}


async def expire_drop_request(
    *,
    request_row: object,
    now: datetime | None = None,
    db: Any | None = None,
    ws_manager: Any | None = None,
) -> bool:
    if getattr(request_row, "type", None) != "drop":
        return False
    if getattr(request_row, "status", None) not in EXPIRABLE_DROP_STATUSES:
        return False

    resolved_at = now or datetime.now(tz=timezone.utc)
    client = db or prisma

    requester_assignment = getattr(request_row, "requester_assignment", None)
    requester_shift = getattr(requester_assignment, "shift", None) if requester_assignment is not None else None
    location_id = getattr(requester_shift, "location_id", None)

    updated = await client.swaprequest.update(
        where={"id": request_row.id},
        data={
            "status": "EXPIRED",
            "resolved_at": resolved_at,
            "resolution_note": "Drop request expired before shift start.",
            "version": getattr(request_row, "version", 0) + 1,
        },
    )

    await create_audit_log(
        actor_id=request_row.initiated_by,
        action_type="drop.expire",
        entity_type="swap_request",
        entity_id=request_row.id,
        location_id=location_id,
        before_state={"status": request_row.status},
        after_state={"status": "EXPIRED"},
        reason="Expired automatically before shift start (24-hour cutoff).",
        db=client,
    )

    recipient_ids: set[str] = {request_row.initiated_by}
    if getattr(request_row, "pickup_user_id", None):
        recipient_ids.add(request_row.pickup_user_id)

    if location_id:
        manager_links = await client.managerlocationassignment.find_many(where={"location_id": location_id})
        for link in manager_links:
            recipient_ids.add(link.manager_id)

    notifications: list[object] = []
    for user_id in sorted(recipient_ids):
        if user_id == request_row.initiated_by:
            message = "Your drop request expired before shift start."
        elif user_id == getattr(request_row, "pickup_user_id", None):
            message = "A drop request you picked up expired before manager approval."
        else:
            message = "A staff drop request expired before shift start."
        notif = await create_notification(
            user_id=user_id,
            notif_type="drop.expired",
            message=message,
            payload={"dropRequestId": request_row.id},
            db=client,
            ws_manager=None,
        )
        notifications.append(notif)

    if ws_manager is not None:
        participant_ids = [request_row.initiated_by] + (
            [request_row.pickup_user_id] if getattr(request_row, "pickup_user_id", None) else []
        )
        await ws_manager.emit_to_users(
            participant_ids,
            "swap.status_changed",
            {"swapRequestId": request_row.id, "newStatus": "EXPIRED"},
        )
        for notif in notifications:
            await ws_manager.emit_to_user(
                notif.user_id,
                "notification.new",
                {
                    "notificationId": notif.id,
                    "type": notif.type,
                    "message": notif.message,
                },
            )

    request_row.status = updated.status
    return True


async def expire_due_drop_requests(
    *,
    now: datetime | None = None,
    db: Any | None = None,
    ws_manager: Any | None = None,
) -> int:
    resolved_at = now or datetime.now(tz=timezone.utc)
    client = db or prisma
    rows = await client.swaprequest.find_many(
        where={
            "type": "drop",
            "status": {"in": sorted(EXPIRABLE_DROP_STATUSES)},
        },
        include={"requester_assignment": {"include": {"shift": True}}},
    )
    count = 0
    for row in rows:
        expires_at = getattr(row, "expires_at", None)
        if expires_at is None:
            requester_assignment = getattr(row, "requester_assignment", None)
            shift = getattr(requester_assignment, "shift", None) if requester_assignment is not None else None
            if shift is None or getattr(shift, "start_utc", None) is None:
                continue
            expires_at = shift.start_utc - timedelta(hours=24)
        if expires_at >= resolved_at:
            continue
        expired = await expire_drop_request(
            request_row=row,
            now=resolved_at,
            db=client,
            ws_manager=ws_manager,
        )
        if expired:
            count += 1
    return count
