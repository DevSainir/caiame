"""The profile endpoint: who may change what, and about whom."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from core import deps
from main import app
from services.rate_limit import RateLimitService
from tests.support.factories import make_user
from tests.support.fakes import FakeCounterStore, FakeRefreshTokenRepo, FakeUserRepo

PASSWORD = "correct-horse-battery"


@pytest.fixture
def storage() -> tuple[FakeUserRepo, FakeRefreshTokenRepo]:
    """Two accounts, so "edits only their own" is testable rather than assumed."""
    return FakeUserRepo(
        [
            make_user(email="student@example.org", password=PASSWORD),
            make_user(email="other@example.org", password=PASSWORD),
        ]
    ), FakeRefreshTokenRepo()


@pytest.fixture
def client(storage: tuple[FakeUserRepo, FakeRefreshTokenRepo]) -> Iterator[TestClient]:
    """
    The app wired to in-memory repositories.

    The rate limiter gets a counter of its own too: sharing the real one would make every
    test depend on how many tests signed in before it.
    """
    user_repo, refresh_repo = storage
    limiter = RateLimitService(store=FakeCounterStore())
    app.dependency_overrides[deps.get_user_repo] = lambda: user_repo
    app.dependency_overrides[deps.get_refresh_token_repo] = lambda: refresh_repo
    app.dependency_overrides[deps.get_rate_limit_service] = lambda: limiter

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def sign_in(client: TestClient, email: str = "student@example.org") -> str:
    """Sign in and return the access token."""
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    token: str = response.json()["access_token"]
    return token


async def test_a_name_can_be_set_after_registration(client: TestClient) -> None:
    """Registration asks for an address and a password only, so the name starts empty."""
    token = sign_in(client)

    response = client.patch(
        "/api/v1/users/me",
        json={"full_name": "Айгуль Садыкова"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Айгуль Садыкова"


async def test_surrounding_spaces_are_trimmed(client: TestClient) -> None:
    """A name pasted with a trailing space is the same name."""
    token = sign_in(client)

    response = client.patch(
        "/api/v1/users/me",
        json={"full_name": "  Марат Осмонов  "},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.json()["full_name"] == "Марат Осмонов"


async def test_editing_a_profile_needs_a_token(client: TestClient) -> None:
    """Closed by default: without a token there is nothing to edit."""
    response = client.patch("/api/v1/users/me", json={"full_name": "Кто-то"})

    assert response.status_code == 401


async def test_the_token_decides_whose_profile_changes(
    client: TestClient, storage: tuple[FakeUserRepo, FakeRefreshTokenRepo]
) -> None:
    """
    The account comes from the token, never from the payload.

    An endpoint that accepts a user id is an endpoint that edits other people's profiles;
    the extra field here must be ignored rather than obeyed.
    """
    user_repo = storage[0]
    other = next(user for user in user_repo.users if user.email == "other@example.org")
    token = sign_in(client, "student@example.org")

    client.patch(
        "/api/v1/users/me",
        json={"full_name": "Подменённое имя", "id": str(other.id), "user_id": str(other.id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert other.full_name == ""


@pytest.mark.parametrize("name", ["", "   ", "и" * 201])
async def test_unusable_names_are_rejected(client: TestClient, name: str) -> None:
    """An empty display name would render as a blank profile."""
    token = sign_in(client)

    response = client.patch(
        "/api/v1/users/me",
        json={"full_name": name},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
