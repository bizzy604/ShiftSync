import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager


class AssignmentLockManager:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._guard = asyncio.Lock()

    @asynccontextmanager
    async def user_lock(self, user_id: str):
        async with self._guard:
            lock = self._locks[user_id]
        await lock.acquire()
        try:
            yield
        finally:
            lock.release()
