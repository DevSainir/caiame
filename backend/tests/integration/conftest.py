"""
Fixtures for the tier that talks to a real PostgreSQL.

These tests exist for behaviour that in-memory fakes cannot show: anything that depends on
a transaction actually committing or rolling back. The suite skips itself when no database
is reachable, so a laptop without Docker still runs everything else.
"""

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import core.db
from core import deps
from core.config import get_settings
from main import app
from services.rate_limit import RateLimitService
from tests.support.fakes import FakeCounterStore

BACKEND_ROOT = Path(__file__).resolve().parents[2]
TEST_DATABASE = "caiame_test"
TABLES = (
    "refresh_tokens",
    "course_units",
    "course_questions",
    "course_benefits",
    "reviews",
    "unit_progress",
    "courses",
    "users",
    "specializations",
    "accreditations",
)


def _url(database: str) -> URL:
    """The configured connection, pointed at another database on the same server."""
    return make_url(get_settings().database_url).set(database=database)


async def _create_database_if_missing() -> None:
    """Create the test database once. Connecting to `postgres` first, as it always exists."""
    engine = create_async_engine(_url("postgres"), poolclass=NullPool, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DATABASE}
            )
            if not exists:
                await connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE}"'))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def migrated_database() -> URL:
    """A test database with migrations applied, or a skip when PostgreSQL is not running."""
    try:
        asyncio.run(_create_database_if_missing())
    except Exception as error:  # any connection failure means "no database"
        pytest.skip(f"PostgreSQL is unavailable: {error}")

    url = _url(TEST_DATABASE)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    command.upgrade(config, "head")
    return url


@pytest.fixture
def client(migrated_database: URL, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """
    The app bound to the test database, with the production session dependency untouched.

    Only the session factory is swapped, so the commit and rollback rules under test are
    the ones the application actually runs.
    """
    asyncio.run(_truncate(migrated_database))

    engine = create_async_engine(migrated_database, poolclass=NullPool)
    monkeypatch.setattr(
        core.db, "session_factory", async_sessionmaker(engine, expire_on_commit=False)
    )
    # These tests are about transactions, not about throttling: a shared Redis counter would
    # carry over between runs and start refusing the fixtures.
    app.dependency_overrides[deps.get_rate_limit_service] = lambda: RateLimitService(
        store=FakeCounterStore()
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


async def _truncate(url: URL) -> None:
    """Empty every table, so one test never inherits another's rows."""
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
    finally:
        await engine.dispose()
