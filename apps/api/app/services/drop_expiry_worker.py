"""
MODULE: /apps/api/app/services/drop_expiry_worker.py

FUNCTION:
    Implements reusable domain service logic for `drop_expiry_worker` workflows.

DEPENDENCIES:
    - /apps/api/app/main.py
    - /apps/api/app/modules/swaps/service.py

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.modules.swaps.service import expire_due_drop_requests_for_worker


async def expire_drop_requests_once(app: Any) -> int:
    """Expire drop requests once.
    
    Args:
        app: Input parameter `app` used by this operation.
    
    Returns:
        Result typed as `int`.
    """
    now = datetime.now(tz=timezone.utc)
    ws_manager = getattr(app.state, "ws_manager", None)
    return await expire_due_drop_requests_for_worker(now=now, ws_manager=ws_manager)


async def run_drop_expiry_worker(app: Any, interval_seconds: int = 60) -> None:
    """Run drop expiry worker.
    
    Args:
        app: Input parameter `app` used by this operation.
        interval_seconds: Input parameter `interval_seconds` used by this operation.
    
    Returns:
        None.
    """
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
