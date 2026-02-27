import asyncio
from datetime import datetime, timezone
from typing import Any

from app.services.drop_expiry import expire_due_drop_requests


async def expire_drop_requests_once(app: Any) -> int:
    now = datetime.now(tz=timezone.utc)
    ws_manager = getattr(app.state, "ws_manager", None)
    return await expire_due_drop_requests(now=now, ws_manager=ws_manager)


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
