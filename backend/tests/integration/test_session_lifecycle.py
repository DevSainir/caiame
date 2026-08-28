"""
The session rules against a real database.

Everything here failed to show up in the component tier: with in-memory repositories there
is no transaction, so a revocation that gets rolled back still looks like a revocation.
"""

from fastapi.testclient import TestClient

from routers.auth import REFRESH_COOKIE

PASSWORD = "correct-horse-battery"


def register(client: TestClient, email: str = "student@example.org") -> str:
    """Create an account and return the refresh cookie it was given."""
    response = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201
    cookie: str = client.cookies[REFRESH_COOKIE]
    return cookie


async def test_replay_survives_the_refusal_and_ends_the_honest_session(
    client: TestClient,
) -> None:
    """
    Revoking a replayed family must be committed, not rolled back with the 401.

    This is the trap: the refusal and the revocation happen in the same request, and the
    session dependency rolls back on an exception. Raising to refuse would undo the
    revocation, and the stolen token would keep working for a week.
    """
    stolen = register(client)
    client.post("/api/v1/auth/refresh")

    replay = client.post("/api/v1/auth/refresh", cookies={REFRESH_COOKIE: stolen})
    honest = client.post("/api/v1/auth/refresh")

    assert replay.status_code == 401
    assert replay.json()["detail"] == "refresh_token_reused"
    assert honest.status_code == 401


async def test_rotation_persists_between_requests(client: TestClient) -> None:
    """The spent token is dead in the database, not only in the response."""
    first = register(client)

    assert client.post("/api/v1/auth/refresh").status_code == 200

    replay = client.post("/api/v1/auth/refresh", cookies={REFRESH_COOKIE: first})
    assert replay.status_code == 401


async def test_logout_is_committed(client: TestClient) -> None:
    """Signing out has to outlive the request that performed it."""
    cookie = register(client)

    assert client.post("/api/v1/auth/logout").status_code == 204

    assert client.post("/api/v1/auth/refresh", cookies={REFRESH_COOKIE: cookie}).status_code == 401


async def test_registration_is_persisted_and_the_address_is_unique(client: TestClient) -> None:
    """The account survives the request, and the unique index is real, not just a check."""
    register(client, "twice@example.org")

    second = client.post(
        "/api/v1/auth/register", json={"email": "twice@example.org", "password": PASSWORD}
    )

    assert second.status_code == 409


async def test_signing_in_again_starts_an_independent_session(client: TestClient) -> None:
    """
    Two devices are two families: ending one must not end the other.

    Revoking by family rather than by user is what makes "log out everywhere" a separate
    feature instead of an accident.
    """
    register(client, "two-devices@example.org")
    first_device = client.cookies[REFRESH_COOKIE]

    second = client.post(
        "/api/v1/auth/login", json={"email": "two-devices@example.org", "password": PASSWORD}
    )
    assert second.status_code == 200

    client.post("/api/v1/auth/logout")

    assert (
        client.post("/api/v1/auth/refresh", cookies={REFRESH_COOKIE: first_device}).status_code
        == 200
    )
