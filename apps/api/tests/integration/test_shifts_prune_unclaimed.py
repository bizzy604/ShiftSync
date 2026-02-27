"""
MODULE: /apps/api/tests/integration/test_shifts_prune_unclaimed.py

FUNCTION:
    Contains integration tests covering `test_shifts_prune_unclaimed` API and workflow
    behavior.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module guards against regressions and documents expected behavior for future
    contributors.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import importlib

import pytest

from app.modules import shifts

shifts_service = importlib.import_module("app.modules.shifts.service")


@pytest.mark.asyncio
async def test_prune_past_unclaimed_shifts_hides_only_understaffed_past_shifts(monkeypatch) -> None:
    now = datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc)
    past_understaffed = SimpleNamespace(
        id="shift-1",
        status="draft",
        end_utc=now - timedelta(hours=2),
        headcount_needed=2,
    )
    past_filled = SimpleNamespace(
        id="shift-2",
        status="published",
        end_utc=now - timedelta(hours=1),
        headcount_needed=1,
    )
    future_understaffed = SimpleNamespace(
        id="shift-3",
        status="draft",
        end_utc=now + timedelta(hours=4),
        headcount_needed=3,
    )
    past_cancelled = SimpleNamespace(
        id="shift-4",
        status="cancelled",
        end_utc=now - timedelta(hours=1),
        headcount_needed=1,
    )

    fake_prisma = SimpleNamespace(
        shiftassignment=SimpleNamespace(
            find_many=AsyncMock(
                return_value=[
                    SimpleNamespace(shift_id="shift-1"),
                    SimpleNamespace(shift_id="shift-2"),
                ]
            )
        )
    )
    monkeypatch.setattr(shifts_service, "prisma", fake_prisma)

    result = await shifts._prune_past_unclaimed_shifts(
        [past_understaffed, past_filled, future_understaffed, past_cancelled],
        now_utc=now,
    )

    assert [item.id for item in result] == ["shift-2", "shift-3", "shift-4"]


