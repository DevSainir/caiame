"""
The counter against a real Redis.

The unit tests use an in-memory stand-in, which cannot show the thing that actually breaks
in production: a window that never closes because the expiry is refreshed on every hit.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
from redis.asyncio import Redis

from core.config import get_settings
from integrations.redis import RedisCounterStore

KEY = "test:rate-limit:counter"


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    """
    A Redis client, or a skip when nothing is listening.

    Async on purpose: an asyncio Redis connection belongs to the loop that opened it, and a
    client built in a different loop fails with "attached to a different loop".
    """
    client = Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        await client.ping()
    except Exception as error:  # any connection failure means "no Redis"
        pytest.skip(f"Redis is unavailable: {error}")
    await client.delete(KEY)
    yield client
    await client.delete(KEY)
    await client.aclose()


async def test_counting_and_expiry(redis: Redis) -> None:
    """The count rises, and the first hit is what sets the window."""
    store = RedisCounterStore(redis)

    first_count, first_ttl = await store.increment(KEY, window_seconds=60)
    second_count, second_ttl = await store.increment(KEY, window_seconds=60)

    assert (first_count, second_count) == (1, 2)
    assert 0 < second_ttl <= first_ttl


async def test_the_window_does_not_slide(redis: Redis) -> None:
    """
    A steady stream of attempts must not keep the window open forever.

    Refreshing the TTL on every hit is the classic mistake: the counter then never resets
    for an attacker who keeps trying, but also never resets for the user they locked out.
    """
    store = RedisCounterStore(redis)
    await store.increment(KEY, window_seconds=60)
    await asyncio.sleep(1.1)

    _, ttl = await store.increment(KEY, window_seconds=60)

    assert ttl < 60
