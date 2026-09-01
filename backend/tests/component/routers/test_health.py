"""
Liveness and readiness are two different questions, and answering them with one number is
how an outage stays invisible.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from core import deps
from main import app
from services.health import HealthService


class FakeRedis:
    """A cache that answers, or refuses to."""

    def __init__(self, *, alive: bool = True) -> None:
        self.alive = alive

    async def ping(self) -> bool:
        """Answer like Redis does, or fail like it does when it is down."""
        if not self.alive:
            raise ConnectionError("no route to cache")
        return True


class FakeDatabase:
    """A database that answers the check query, or refuses to."""

    def __init__(self, *, alive: bool = True) -> None:
        self.alive = alive

    async def ping(self) -> None:
        """Answer, or fail the way an unreachable database does."""
        if not self.alive:
            raise ConnectionError("no route to database")


def client_with(*, database: bool = True, cache: bool = True) -> Iterator[TestClient]:
    """The app with both dependencies replaced by stand-ins in the state under test."""
    app.dependency_overrides[deps.get_health_service] = lambda: HealthService(
        database=FakeDatabase(alive=database), cache=FakeRedis(alive=cache)
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def healthy() -> Iterator[TestClient]:
    """Everything answering."""
    yield from client_with()


def test_readiness_says_ok_when_everything_answers(healthy: TestClient) -> None:
    """The straight case: a monitor watching this should see nothing."""
    response = healthy.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True, "cache": True}


def test_readiness_fails_when_the_database_is_unreachable() -> None:
    """
    A process that is running but cannot reach its database serves errors and looks alive.

    503 is what makes that visible from outside, which is the whole point of the route.
    """
    for test_client in client_with(database=False):
        response = test_client.get("/api/v1/health/ready")

        assert response.status_code == 503
        assert response.json()["database"] is False


def test_liveness_stays_simple_while_the_database_is_down() -> None:
    """
    Liveness must not follow the database.

    The container health check reads it, and restarting the API because the database
    blinked turns one outage into two.
    """
    for test_client in client_with(database=False):
        assert test_client.get("/api/v1/health").status_code == 200


def test_every_answer_carries_an_identifier(healthy: TestClient) -> None:
    """«It broke around noon» needs something to match against in the log."""
    response = healthy.get("/api/v1/health")

    assert response.headers.get("X-Request-Id")
