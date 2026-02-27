"""
MODULE: /apps/api/tests/integration/test_swaps_notify_qualified.py

FUNCTION:
    Contains integration tests covering `test_swaps_notify_qualified` API and workflow
    behavior.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module guards against regressions and documents expected behavior for future
    contributors.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.api.routes import swaps


@pytest.mark.asyncio
async def test_notify_qualified_requires_open_drop_status(monkeypatch) -> None:
    row = SimpleNamespace(
        id="drop-1",
        type="drop",
        status="PENDING_MANAGER",
        requester_assignment=SimpleNamespace(shift=SimpleNamespace()),
    )

    fake_prisma = SimpleNamespace(
        swaprequest=SimpleNamespace(find_unique=AsyncMock(return_value=row)),
    )
    monkeypatch.setattr(swaps, "prisma", fake_prisma)

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ws_manager=None)))
    current_user = CurrentUser(id="manager-1", role="manager", location_ids=["loc-1"])

    with pytest.raises(HTTPException) as exc:
        await swaps.notify_qualified_staff(
            request_id="drop-1",
            request=request,
            current_user=current_user,
        )

    assert exc.value.status_code == 422
    assert "not open for notifications" in str(exc.value.detail)
