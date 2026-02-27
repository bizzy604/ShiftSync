"""
MODULE: /apps/api/tests/unit/test_locations_module.py

FUNCTION:
    Covers locations module repository and service behavior with isolated unit tests.

DEPENDENCIES:
    - /apps/api/app/modules/locations/repository.py
    - /apps/api/app/modules/locations/service.py

IMPORTANCE:
    These tests lock the modular locations boundary behavior during migration and reduce
    regression risk when route handlers become thinner.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.deps import CurrentUser
from app.modules.locations.exceptions import LocationAccessDeniedError
from app.modules.locations.repository import LocationsRepository
from app.modules.locations.service import get_location


@pytest.mark.asyncio
async def test_locations_repository_lists_all_locations_ordered_by_name() -> None:
    fake_db = SimpleNamespace(location=SimpleNamespace(find_many=AsyncMock(return_value=[])))
    repo = LocationsRepository(db=fake_db)

    result = await repo.list_all_locations()

    assert result == []
    fake_db.location.find_many.assert_awaited_once_with(order={"name": "asc"})


@pytest.mark.asyncio
async def test_get_location_denies_staff_without_active_certification() -> None:
    repo = SimpleNamespace(
        find_location=AsyncMock(return_value=SimpleNamespace(id="loc-1")),
        find_staff_location_certification=AsyncMock(return_value=None),
    )

    with pytest.raises(LocationAccessDeniedError):
        await get_location(
            location_id="loc-1",
            current_user=CurrentUser(id="staff-1", role="staff", location_ids=[]),
            repository=repo,
        )
