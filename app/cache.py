import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from redis.asyncio import Redis

T = TypeVar("T")


class Cache:
    def __init__(self, client: Redis | None):
        self.client = client

    async def get_or_create(self, key: str, ttl_seconds: int, factory: Callable[[], Awaitable[T]]) -> T:
        if self.client is None:
            return await factory()

        cached = await self.client.get(key)
        if cached:
            return json.loads(cached)

        value = await factory()
        await self.client.setex(key, ttl_seconds, json.dumps(value, default=str))
        return value

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()


def build_cache(redis_url: str) -> Cache:
    if not redis_url.strip():
        return Cache(None)

    return Cache(Redis.from_url(redis_url, decode_responses=True))
