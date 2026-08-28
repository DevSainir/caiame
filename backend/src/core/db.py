from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import get_settings

_settings = get_settings()

engine = create_async_engine(_settings.database_url, echo=_settings.echo_sql, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """
    Own the transaction boundary: one request, one transaction.

    Services and repositories never commit. The commit happens here on a successful exit,
    which is also why a rollback on failure needs no explicit call in business code.
    """
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        await session.commit()
