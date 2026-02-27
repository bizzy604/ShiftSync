"""
MODULE: /apps/api/tests/unit/test_audit_module.py

FUNCTION:
    Covers audit module repository and service behavior with isolated unit tests.

DEPENDENCIES:
    - /apps/api/app/modules/audit/repository.py
    - /apps/api/app/modules/audit/service.py

IMPORTANCE:
    These tests lock query filtering and response mapping behavior for the migrated
    audit module boundary.
"""

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.deps import CurrentUser
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import build_where, export_audit_logs, list_audit_logs


@pytest.mark.asyncio
async def test_audit_repository_lists_logs_with_actor_relation() -> None:
    fake_db = SimpleNamespace(auditlog=SimpleNamespace(find_many=AsyncMock(return_value=[])))
    repo = AuditRepository(db=fake_db)

    await repo.list_audit_logs(where={"entity_type": "shift"}, skip=0, take=10)

    fake_db.auditlog.find_many.assert_awaited_once_with(
        where={"entity_type": "shift"},
        include={"actor": True},
        order={"created_at": "desc"},
        skip=0,
        take=10,
    )


def test_build_where_scopes_manager_requests_to_owned_locations() -> None:
    where = build_where(
        current_user=CurrentUser(id="mgr-1", role="manager", location_ids=["loc-1", "loc-2"]),
        entity_type=None,
        entity_id=None,
        location_id=None,
        start_date=None,
        end_date=None,
    )

    assert where["location_id"] == {"in": ["loc-1", "loc-2"]}


@pytest.mark.asyncio
async def test_list_audit_logs_maps_actor_name_and_pagination() -> None:
    item = SimpleNamespace(
        id="log-1",
        actor_id="user-1",
        actor=SimpleNamespace(name="Alice"),
        action_type="shift.create",
        entity_type="shift",
        entity_id="shift-1",
        before_state={"status": "draft"},
        after_state={"status": "published"},
        reason=None,
        location_id="loc-1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    repo = SimpleNamespace(
        list_audit_logs=AsyncMock(return_value=[item]),
        count_audit_logs=AsyncMock(return_value=1),
    )

    response = await list_audit_logs(
        current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
        entity_type=None,
        entity_id=None,
        location_id=None,
        start_date=None,
        end_date=None,
        page=1,
        limit=50,
        repository=repo,
    )

    assert response.pagination == {"page": 1, "limit": 50, "total": 1}
    assert response.logs[0].actor_name == "Alice"


@pytest.mark.asyncio
async def test_export_audit_logs_uses_date_range_in_filename() -> None:
    repo = SimpleNamespace(export_audit_logs=AsyncMock(return_value=[]))

    filename, rows = await export_audit_logs(
        current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
        entity_type=None,
        entity_id=None,
        location_id=None,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 7),
        repository=repo,
    )

    assert filename == "audit_log_2026-01-01_2026-01-07.csv"
    assert rows == []
