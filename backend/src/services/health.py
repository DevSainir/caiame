"""
Whether the application can actually serve.

Kept apart from liveness deliberately. The container health check reads liveness and
restarts the process when it stops answering; restarting the API because the database
blinked turns one outage into two. This is the question a monitor should ask instead.
"""

from collections.abc import Awaitable, Callable
from typing import Protocol

from core.logger import get_logger
from schemas.health import ReadinessOut

logger = get_logger(__name__)


class DatabaseProbe(Protocol):
    """The database side of the check."""

    async def ping(self) -> None:
        """Raise unless the database answers."""
        ...


class CacheProbe(Protocol):
    """
    The cache side of the check.

    Written as a plain method returning an awaitable rather than as `async def`: that is
    the shape the Redis client has, and a protocol that does not match it would be a
    protocol nothing can satisfy.
    """

    def ping(self) -> Awaitable[bool]:
        """Raise unless the cache answers."""
        ...


class HealthService:
    """Asks the two things the application cannot work without whether they answer."""

    def __init__(self, *, database: DatabaseProbe, cache: CacheProbe) -> None:
        self.database = database
        self.cache = cache

    async def readiness(self) -> ReadinessOut:
        """
        The state of both dependencies, as one answer.

        Every kind of failure collapses into «no» — unreachable, refusing, timing out —
        because a monitor needs a state, not a diagnosis. The diagnosis goes to the log,
        where somebody can read it.
        """
        database = await self._answers(self.database.ping, "database")
        cache = await self._answers(self.cache.ping, "cache")
        return ReadinessOut(
            status="ok" if database and cache else "degraded",
            database=database,
            cache=cache,
        )

    @staticmethod
    async def _answers(check: Callable[[], Awaitable[object]], name: str) -> bool:
        """Run one probe and turn any failure into «no»."""
        try:
            await check()
        except Exception:
            logger.exception("readiness check failed: %s", name)
            return False
        return True
