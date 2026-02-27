import time
from typing import Optional

from redis.asyncio import Redis


class SessionStore:
    """
    Uses Redis when available, with an in-memory fallback for local development.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis: Optional[Redis] = None
        self._memory: dict[str, float] = {}

    async def connect(self) -> None:
        try:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()
        except Exception:
            self._redis = None

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if self._redis is not None:
            await self._redis.setex(key, ttl_seconds, value)
            return
        self._memory[key] = time.time() + ttl_seconds

    async def exists(self, key: str) -> bool:
        if self._redis is not None:
            exists_value = await self._redis.exists(key)
            return exists_value == 1

        expiry = self._memory.get(key)
        if expiry is None:
            return False
        if expiry < time.time():
            self._memory.pop(key, None)
            return False
        return True

    async def touch(self, key: str, ttl_seconds: int) -> bool:
        if self._redis is not None:
            # EXPIRE returns 1 when key exists and timeout set.
            updated = await self._redis.expire(key, ttl_seconds)
            return updated == 1

        expiry = self._memory.get(key)
        if expiry is None:
            return False
        if expiry < time.time():
            self._memory.pop(key, None)
            return False
        self._memory[key] = time.time() + ttl_seconds
        return True

    async def delete(self, key: str) -> None:
        if self._redis is not None:
            await self._redis.delete(key)
            return
        self._memory.pop(key, None)
