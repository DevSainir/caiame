from typing import Protocol

from core.logger import get_logger

logger = get_logger(__name__)


class RateLimitExceededError(Exception):
    """Too many attempts in the window. Carries how long the caller must wait."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"rate limit exceeded, retry after {retry_after}s")
        self.retry_after = retry_after


class CounterStore(Protocol):
    """Fixed-window counter storage."""

    async def increment(self, key: str, *, window_seconds: int) -> tuple[int, int]:
        """Add one hit and return the running count and the seconds left in the window."""
        ...


class RateLimitService:
    """Counts attempts and refuses the ones past the allowance."""

    def __init__(self, *, store: CounterStore) -> None:
        self.store = store

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> None:
        """
        Register an attempt and raise once the allowance is spent.

        Fails open on a storage error, on purpose. A limiter that refuses everything when
        Redis hiccups turns a cache outage into "nobody can sign in" — a worse incident
        than a few minutes without brute-force protection. The failure is logged loudly so
        it does not stay unnoticed.
        """
        try:
            count, ttl = await self.store.increment(key, window_seconds=window_seconds)
        except Exception:
            logger.exception("rate limit store unavailable, allowing request for key %s", key)
            return

        if count > limit:
            raise RateLimitExceededError(max(ttl, 1))
