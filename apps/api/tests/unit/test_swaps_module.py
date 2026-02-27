"""
MODULE: /apps/api/tests/unit/test_swaps_module.py

FUNCTION:
    Covers swaps module service behavior that is shared with worker orchestration.

DEPENDENCIES:
    - /apps/api/app/modules/swaps/service.py
    - /apps/api/app/services/drop_expiry_worker.py

IMPORTANCE:
    This test guards the module boundary used by the drop expiry worker so background
    expiry behavior remains correctly delegated to swaps service logic.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.modules.swaps import service as swaps_service


@pytest.mark.asyncio
async def test_expire_due_drop_requests_for_worker_forwards_arguments(monkeypatch) -> None:
    """Ensure worker helper delegates to drop expiry service with unchanged arguments."""

    delegated = AsyncMock(return_value=3)
    monkeypatch.setattr(swaps_service, "expire_due_drop_requests", delegated)

    now = datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc)
    ws_manager = object()

    result = await swaps_service.expire_due_drop_requests_for_worker(now=now, ws_manager=ws_manager)

    assert result == 3
    delegated.assert_awaited_once_with(now=now, ws_manager=ws_manager)
