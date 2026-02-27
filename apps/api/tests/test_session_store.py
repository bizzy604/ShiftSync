import time

import pytest

from app.core.session_store import SessionStore


@pytest.mark.asyncio
async def test_touch_extends_memory_ttl_for_existing_session() -> None:
    store = SessionStore(redis_url=None)
    await store.set("session:test", "user-1", ttl_seconds=5)
    before = store._memory["session:test"]

    touched = await store.touch("session:test", ttl_seconds=60)

    assert touched is True
    after = store._memory["session:test"]
    assert after > before + 50


@pytest.mark.asyncio
async def test_touch_returns_false_for_expired_memory_session() -> None:
    store = SessionStore(redis_url=None)
    store._memory["session:expired"] = time.time() - 5

    touched = await store.touch("session:expired", ttl_seconds=60)

    assert touched is False
    assert "session:expired" not in store._memory
