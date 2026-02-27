"""
MODULE: /apps/api/tests/integration/test_skills_routes.py

FUNCTION:
    Contains integration tests covering `test_skills_routes` API and workflow behavior.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module guards against regressions and documents expected behavior for future
    contributors.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.deps import CurrentUser
from app.modules import skills
from app.core.errors import AppError
from app.modules.skills import service as skills_service


@pytest.mark.asyncio
async def test_create_skill_success(monkeypatch) -> None:
    audit_calls: list[dict] = []

    async def fake_audit(**kwargs):
        audit_calls.append(kwargs)

    tx = SimpleNamespace(
        skill=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(id="skill-1", name="expeditor")))
    )
    fake_prisma = SimpleNamespace(
        skill=SimpleNamespace(find_many=AsyncMock(return_value=[])),
        tx=None,
    )

    class _TxContext:
        async def __aenter__(self):
            return tx

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_prisma.tx = lambda: _TxContext()

    monkeypatch.setattr(skills_service, "prisma", fake_prisma)
    monkeypatch.setattr(skills_service, "create_audit_log", fake_audit)

    result = await skills.create_skill(
        payload=skills.SkillCreateRequest(name="Expeditor"),
        current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
    )

    assert result.id == "skill-1"
    assert result.name == "expeditor"
    assert audit_calls and audit_calls[0]["action_type"] == "skill.catalog.add"


@pytest.mark.asyncio
async def test_create_skill_duplicate_is_rejected(monkeypatch) -> None:
    fake_prisma = SimpleNamespace(
        skill=SimpleNamespace(find_many=AsyncMock(return_value=[SimpleNamespace(id="skill-1", name="Server")])),
    )
    monkeypatch.setattr(skills_service, "prisma", fake_prisma)

    with pytest.raises(AppError) as exc:
        await skills.create_skill(
            payload=skills.SkillCreateRequest(name="server"),
            current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_delete_skill_in_use_is_rejected(monkeypatch) -> None:
    fake_prisma = SimpleNamespace(
        skill=SimpleNamespace(find_unique=AsyncMock(return_value=SimpleNamespace(id="skill-1", name="server"))),
        userskill=SimpleNamespace(count=AsyncMock(return_value=2)),
        shift=SimpleNamespace(count=AsyncMock(return_value=0)),
    )
    monkeypatch.setattr(skills_service, "prisma", fake_prisma)

    with pytest.raises(AppError) as exc:
        await skills.delete_skill(
            skill_id="skill-1",
            current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_delete_skill_success(monkeypatch) -> None:
    audit_calls: list[dict] = []

    async def fake_audit(**kwargs):
        audit_calls.append(kwargs)

    tx = SimpleNamespace(skill=SimpleNamespace(delete=AsyncMock(return_value=None)))
    fake_prisma = SimpleNamespace(
        skill=SimpleNamespace(find_unique=AsyncMock(return_value=SimpleNamespace(id="skill-1", name="host"))),
        userskill=SimpleNamespace(count=AsyncMock(return_value=0)),
        shift=SimpleNamespace(count=AsyncMock(return_value=0)),
        tx=None,
    )

    class _TxContext:
        async def __aenter__(self):
            return tx

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_prisma.tx = lambda: _TxContext()

    monkeypatch.setattr(skills_service, "prisma", fake_prisma)
    monkeypatch.setattr(skills_service, "create_audit_log", fake_audit)

    result = await skills.delete_skill(
        skill_id="skill-1",
        current_user=CurrentUser(id="admin-1", role="admin", location_ids=[]),
    )

    assert result == {"deleted": True}
    assert audit_calls and audit_calls[0]["action_type"] == "skill.catalog.remove"


