import asyncio
from datetime import datetime, timezone
from typing import Any

from app.core.database import prisma
from app.services.notifications import create_notification


async def expire_drop_requests_once(app: Any) -> int:
    now = datetime.now(tz=timezone.utc)
    requests = await prisma.swaprequest.find_many(
        where={
            "type": "drop",
            "status": {"in": ["OPEN", "PENDING_MANAGER"]},
            "expires_at": {"lt": now},
        },
        include={"requester_assignment": {"include": {"user": True}}},
    )

    if not requests:
        return 0

    ws_manager = getattr(app.state, "ws_manager", None)
    count = 0
    for item in requests:
        await prisma.swaprequest.update(
            where={"id": item.id},
            data={
                "status": "EXPIRED",
                "resolved_at": now,
                "resolution_note": "Drop request expired before shift start.",
            },
        )
        count += 1

        requester = item.requester_assignment.user if item.requester_assignment else None
        if requester:
            await create_notification(
                user_id=requester.id,
                notif_type="drop.expired",
                message="Your drop request expired before shift start.",
                payload={"dropRequestId": item.id},
                ws_manager=ws_manager,
            )
    return count


async def run_drop_expiry_worker(app: Any, interval_seconds: int = 60) -> None:
    stop_event: asyncio.Event = app.state.drop_expiry_stop_event
    while not stop_event.is_set():
        try:
            await expire_drop_requests_once(app)
        except Exception:
            # Worker is best-effort and should not crash app lifecycle.
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue
