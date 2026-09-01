from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class HealthRepo:
    """The one query that asks the database whether it is answering at all."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ping(self) -> None:
        """
        Run the cheapest possible statement.

        Cheap on purpose: a monitor calls this every few seconds, and a readiness check that
        touches real tables becomes load of its own — and starts failing for reasons that
        have nothing to do with the database being reachable.
        """
        await self.session.execute(text("SELECT 1"))
