"""
The attempt counter.

Two behaviours matter here and neither is obvious from the code: the allowance is spent
*after* the limit is reached, not at it, and a broken counter store lets requests through
rather than locking everyone out.
"""

import pytest

from services.rate_limit import RateLimitExceededError, RateLimitService
from tests.support.fakes import FakeCounterStore


async def test_attempts_up_to_the_limit_are_allowed() -> None:
    """The tenth attempt of ten still works; refusing at the limit costs a real attempt."""
    service = RateLimitService(store=FakeCounterStore())

    for _ in range(10):
        await service.hit("login:account:doctor@example.org", limit=10, window_seconds=900)


async def test_the_attempt_past_the_limit_is_refused() -> None:
    """One over the allowance is where the refusal starts."""
    service = RateLimitService(store=FakeCounterStore())
    for _ in range(10):
        await service.hit("login:account:doctor@example.org", limit=10, window_seconds=900)

    with pytest.raises(RateLimitExceededError):
        await service.hit("login:account:doctor@example.org", limit=10, window_seconds=900)


async def test_the_refusal_says_how_long_to_wait() -> None:
    """A 429 without Retry-After leaves the client guessing, and clients guess badly."""
    service = RateLimitService(store=FakeCounterStore())
    await service.hit("login:ip:203.0.113.10", limit=1, window_seconds=900)

    with pytest.raises(RateLimitExceededError) as refusal:
        await service.hit("login:ip:203.0.113.10", limit=1, window_seconds=900)

    assert refusal.value.retry_after == 900


async def test_counters_are_independent() -> None:
    """One account being locked must not lock a different one."""
    service = RateLimitService(store=FakeCounterStore())
    await service.hit("login:account:one@example.org", limit=1, window_seconds=900)

    await service.hit("login:account:two@example.org", limit=1, window_seconds=900)


async def test_a_broken_store_lets_the_request_through() -> None:
    """
    Fail open, deliberately.

    A limiter that refuses everything when Redis hiccups turns a cache outage into "nobody
    can sign in" — a worse incident than a few minutes without brute-force protection.
    """
    service = RateLimitService(store=FakeCounterStore(broken=True))

    for _ in range(50):
        await service.hit("login:ip:203.0.113.10", limit=1, window_seconds=900)
