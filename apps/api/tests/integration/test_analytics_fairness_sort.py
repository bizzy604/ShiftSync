"""
MODULE: /apps/api/tests/integration/test_analytics_fairness_sort.py

FUNCTION:
    Contains integration tests covering `test_analytics_fairness_sort` API and workflow
    behavior.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module guards against regressions and documents expected behavior for future
    contributors.
"""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.deps import CurrentUser
from app.api.routes import analytics


@pytest.mark.asyncio
async def test_fairness_report_sorts_by_absolute_variance(monkeypatch) -> None:
    location = SimpleNamespace(id="loc-1", name="Ocean Ave", iana_timezone="UTC")
    bob = SimpleNamespace(id="u-bob", name="Bob", role="staff", is_active=True, desired_hours_per_week=40)
    charlie = SimpleNamespace(id="u-charlie", name="Charlie", role="staff", is_active=True, desired_hours_per_week=40)
    alice = SimpleNamespace(id="u-alice", name="Alice", role="staff", is_active=True, desired_hours_per_week=40)

    certs = [
        SimpleNamespace(user_id=bob.id, user=bob),
        SimpleNamespace(user_id=charlie.id, user=charlie),
        SimpleNamespace(user_id=alice.id, user=alice),
    ]

    base = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
    shift_b1 = SimpleNamespace(id="s-b1", start_utc=base, end_utc=base + timedelta(hours=30))
    shift_b2 = SimpleNamespace(id="s-b2", start_utc=base + timedelta(days=2), end_utc=base + timedelta(days=2, hours=30))
    shift_c1 = SimpleNamespace(id="s-c1", start_utc=base + timedelta(days=1), end_utc=base + timedelta(days=1, hours=30))
    shift_a1 = SimpleNamespace(id="s-a1", start_utc=base + timedelta(days=3), end_utc=base + timedelta(days=3, hours=40))

    shifts = [shift_b1, shift_b2, shift_c1, shift_a1]
    assignments = [
        SimpleNamespace(user_id=bob.id, shift=shift_b1, user=bob),
        SimpleNamespace(user_id=bob.id, shift=shift_b2, user=bob),
        SimpleNamespace(user_id=charlie.id, shift=shift_c1, user=charlie),
        SimpleNamespace(user_id=alice.id, shift=shift_a1, user=alice),
    ]

    fake_prisma = SimpleNamespace(
        userlocationcertification=SimpleNamespace(find_many=AsyncMock(return_value=certs)),
        shift=SimpleNamespace(find_many=AsyncMock(return_value=shifts)),
        shiftassignment=SimpleNamespace(find_many=AsyncMock(return_value=assignments)),
    )
    monkeypatch.setattr(analytics, "prisma", fake_prisma)
    monkeypatch.setattr(analytics, "_location_or_404", AsyncMock(return_value=location))

    response = await analytics.fairness_report(
        location_id="loc-1",
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 11),
        current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
    )

    ordered_ids = [row.user_id for row in response.staff]
    assert ordered_ids == [bob.id, charlie.id, alice.id]
