from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import prisma
from app.services.audit import create_audit_log
from app.services.notifications import create_notification


PENDING_SWAP_STATUSES = ["PENDING_ACCEPTEE", "PENDING_MANAGER"]


def _swap_touches_shift(row: object, shift_id: str) -> bool:
    requester_assignment = getattr(row, "requester_assignment", None)
    if requester_assignment is not None and getattr(requester_assignment, "shift_id", None) == shift_id:
        return True
    candidate_assignment = getattr(row, "candidate_assignment", None)
    if candidate_assignment is not None and getattr(candidate_assignment, "shift_id", None) == shift_id:
        return True
    return False


async def _cancel_rows(
    *,
    client: Any,
    rows: list[object],
    actor_id: str,
    reason: str,
    ws_manager: Any | None,
) -> int:
    now = datetime.now(tz=timezone.utc)
    count = 0
    for row in rows:
        requester_assignment = getattr(row, "requester_assignment", None)
        location_id = None
        if requester_assignment is not None:
            shift = getattr(requester_assignment, "shift", None)
            location_id = getattr(shift, "location_id", None)

        updated = await client.swaprequest.update(
            where={"id": row.id},
            data={
                "status": "CANCELLED",
                "resolved_at": now,
                "resolved_by": actor_id,
                "resolution_note": reason,
                "version": row.version + 1,
            },
        )
        await create_audit_log(
            actor_id=actor_id,
            action_type="swap.auto_cancel_shift_edit",
            entity_type="swap_request",
            entity_id=row.id,
            location_id=location_id,
            before_state={"status": row.status},
            after_state={"status": "CANCELLED"},
            reason=reason,
            db=client,
        )

        recipient_ids = {
            row.initiated_by,
            row.target_user_id,
            row.pickup_user_id,
        }
        if location_id:
            manager_links = await client.managerlocationassignment.find_many(where={"location_id": location_id})
            for link in manager_links:
                recipient_ids.add(link.manager_id)

        notifications: list[object] = []
        for user_id in sorted(x for x in recipient_ids if x):
            record = await create_notification(
                user_id=user_id,
                notif_type="swap.cancelled",
                message=reason,
                payload={"swapRequestId": row.id},
                db=client,
                ws_manager=None,
            )
            notifications.append(record)

        if ws_manager is not None:
            if recipient_ids:
                await ws_manager.emit_to_users(
                    [x for x in recipient_ids if x],
                    "swap.status_changed",
                    {"swapRequestId": row.id, "newStatus": "CANCELLED"},
                )
            for record in notifications:
                await ws_manager.emit_to_user(
                    record.user_id,
                    "notification.new",
                    {
                        "notificationId": record.id,
                        "type": record.type,
                        "message": record.message,
                    },
                )
        row.status = updated.status
        count += 1
    return count


async def cancel_pending_swaps_for_shift(
    *,
    shift_id: str,
    actor_id: str,
    reason: str,
    ws_manager: Any | None = None,
    db: Any | None = None,
) -> int:
    client = db or prisma
    rows = await client.swaprequest.find_many(
        where={
            "type": "swap",
            "status": {"in": PENDING_SWAP_STATUSES},
        },
        include={
            "requester_assignment": {"include": {"shift": True}},
            "candidate_assignment": {"include": {"shift": True}},
        },
    )
    target_rows = [row for row in rows if _swap_touches_shift(row, shift_id)]
    if not target_rows:
        return 0

    if db is not None:
        return await _cancel_rows(
            client=client,
            rows=target_rows,
            actor_id=actor_id,
            reason=reason,
            ws_manager=ws_manager,
        )

    async with prisma.tx() as tx:
        return await _cancel_rows(
            client=tx,
            rows=target_rows,
            actor_id=actor_id,
            reason=reason,
            ws_manager=ws_manager,
        )
