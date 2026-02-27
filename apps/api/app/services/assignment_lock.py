"""
MODULE: /apps/api/app/services/assignment_lock.py

FUNCTION:
    Implements reusable domain service logic for `assignment_lock` workflows.

DEPENDENCIES:
    - /apps/api/app/main.py

IMPORTANCE:
    This module keeps domain logic reusable and consistent across routes, workers, and
    future extensions.
"""

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager


class AssignmentLockManager:
    """AssignmentLockManager type."""
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._guard = asyncio.Lock()

    @asynccontextmanager
    async def user_lock(self, user_id: str):
        """User lock.
        
        Args:
            user_id: Target user identifier.
        """
        async with self._guard:
            lock = self._locks[user_id]
        await lock.acquire()
        try:
            yield
        finally:
            lock.release()
