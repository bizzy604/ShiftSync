"""
MODULE: /apps/api/tests/unit/test_analytics_module.py

FUNCTION:
    Covers analytics module repository and service behavior with isolated unit tests.

DEPENDENCIES:
    - /apps/api/app/modules/analytics/repository.py
    - /apps/api/app/modules/analytics/service.py

IMPORTANCE:
    These tests protect the migrated analytics service/repository boundary and key
    validation behavior.
"""

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.deps import CurrentUser
from app.modules.analytics.exceptions import AnalyticsValidationError
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.service import overtime_dashboard


@pytest.mark.asyncio
async def test_analytics_repository_reads_week_shifts_with_expected_filter() -> None:
    fake_db = SimpleNamespace(shift=SimpleNamespace(find_many=AsyncMock(return_value=[])))
    repo = AnalyticsRepository(db=fake_db)
    week_start = datetime(2026, 1, 5)

    await repo.list_week_shifts(location_id="loc-1", week_start=week_start)

    fake_db.shift.find_many.assert_awaited_once_with(
        where={
            "location_id": "loc-1",
            "week_start": week_start,
            "status": {"in": ["draft", "published"]},
        },
        order={"start_utc": "asc"},
    )


@pytest.mark.asyncio
async def test_overtime_dashboard_returns_empty_when_location_has_no_shifts() -> None:
    repo = SimpleNamespace(
        find_location=AsyncMock(return_value=SimpleNamespace(id="loc-1", iana_timezone="UTC")),
        list_week_shifts=AsyncMock(return_value=[]),
    )

    response = await overtime_dashboard(
        location_id="loc-1",
        week_start=date(2026, 1, 5),
        current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
        repository=repo,
    )

    assert response.location_id == "loc-1"
    assert response.total_projected_overtime_cost == 0.0
    assert response.staff == []


@pytest.mark.asyncio
async def test_hours_distribution_rejects_inverted_date_range() -> None:
    from app.modules.analytics.service import hours_distribution

    with pytest.raises(AnalyticsValidationError):
        await hours_distribution(
            location_id="loc-1",
            start_date=date(2026, 1, 7),
            end_date=date(2026, 1, 5),
            current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
            repository=SimpleNamespace(),
        )
