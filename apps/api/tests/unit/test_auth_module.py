"""
MODULE: /apps/api/tests/unit/test_auth_module.py

FUNCTION:
    Covers auth module service and repository behavior with isolated unit tests.

DEPENDENCIES:
    - /apps/api/app/modules/auth/repository.py
    - /apps/api/app/modules/auth/service.py

IMPORTANCE:
    These tests protect cookie-session issuance and auth error semantics introduced by
    the modular auth service layer.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.security import hash_password
from app.modules.auth.exceptions import AuthenticationRequiredError
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import login, refresh_token
from app.schemas.auth import LoginRequest


@pytest.mark.asyncio
async def test_auth_repository_finds_user_by_email_with_assignments() -> None:
    fake_db = SimpleNamespace(user=SimpleNamespace(find_unique=AsyncMock(return_value=None)))
    repo = AuthRepository(db=fake_db)

    await repo.find_user_by_email("alice@example.com")

    fake_db.user.find_unique.assert_awaited_once_with(
        where={"email": "alice@example.com"},
        include={"manager_location_assignments": True},
    )


@pytest.mark.asyncio
async def test_login_issues_cookie_session_for_valid_credentials() -> None:
    user = SimpleNamespace(
        id="u-1",
        name="Alice",
        email="alice@example.com",
        role="manager",
        password_hash=hash_password("password123"),
        is_active=True,
        manager_location_assignments=[SimpleNamespace(location_id="loc-2"), SimpleNamespace(location_id="loc-1")],
    )
    repo = SimpleNamespace(find_user_by_email=AsyncMock(return_value=user))
    session_store = SimpleNamespace(set=AsyncMock(return_value=None))

    result = await login(
        payload=LoginRequest(email="alice@example.com", password="password123"),
        session_store=session_store,
        repository=repo,
    )

    assert result.payload.user.id == "u-1"
    assert result.cookie.token
    assert result.cookie.ttl_seconds > 0
    session_store.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_requires_existing_cookie_token() -> None:
    with pytest.raises(AuthenticationRequiredError):
        await refresh_token(
            token=None,
            session_store=SimpleNamespace(),
            repository=SimpleNamespace(),
        )
