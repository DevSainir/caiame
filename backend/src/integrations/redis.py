from functools import lru_cache

from redis.asyncio import Redis

from core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    """
    One shared Redis client for the process.

    Created lazily: nothing in the catalogue needs Redis, so a broken cache must not stop
    the application from starting.
    """
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


class RedisCounterStore:
    """Fixed-window counters backed by Redis."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def increment(self, key: str, *, window_seconds: int) -> tuple[int, int]:
        """
        Add one hit to the window and report the running count and the seconds left.

        The expiry is set only on the first hit, which is what makes the window fixed:
        refreshing the TTL on every hit would let a steady stream of attempts keep the
        window open forever.
        """
        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            pipeline.ttl(key)
            count, ttl = await pipeline.execute()

        if ttl < 0:
            await self.redis.expire(key, window_seconds)
            ttl = window_seconds
        return int(count), int(ttl)
