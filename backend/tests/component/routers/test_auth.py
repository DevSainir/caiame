"""The auth endpoints end to end, with storage replaced and everything else real."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from core import deps
from main import app
from routers.auth import REFRESH_COOKIE, SESSION_HINT_COOKIE
from services.rate_limit import RateLimitService
from tests.support.factories import make_user
from tests.support.fakes import FakeCounterStore, FakeRefreshTokenRepo, FakeUserRepo

PASSWORD = "correct-horse-battery"


@pytest.fixture
def storage() -> tuple[FakeUserRepo, FakeRefreshTokenRepo]:
    """One user with a real password hash, and empty token storage."""
    return FakeUserRepo([make_user(email="student@example.org", password=PASSWORD)]), (
        FakeRefreshTokenRepo()
    )


@pytest.fixture
def limiter() -> RateLimitService:
    """A real limiter over in-memory counters, so the route's 429 path is the real one."""
    return RateLimitService(store=FakeCounterStore())


@pytest.fixture
def client(
    storage: tuple[FakeUserRepo, FakeRefreshTokenRepo], limiter: RateLimitService
) -> Iterator[TestClient]:
    """The app wired to in-memory repositories."""
    user_repo, refresh_repo = storage
    app.dependency_overrides[deps.get_user_repo] = lambda: user_repo
    app.dependency_overrides[deps.get_refresh_token_repo] = lambda: refresh_repo
    app.dependency_overrides[deps.get_rate_limit_service] = lambda: limiter

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


async def test_registration_returns_a_session_and_sets_the_cookie(client: TestClient) -> None:
    """The happy path: an access token in the body, the refresh token only in a cookie."""
    response = client.post(
        "/api/v1/auth/register", json={"email": "new@example.org", "password": PASSWORD}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "new@example.org"
    assert REFRESH_COOKIE not in body
    assert REFRESH_COOKIE in response.cookies


async def test_refresh_cookie_is_http_only_and_scoped(client: TestClient) -> None:
    """
    The cookie must be unreadable by page scripts and not sent with every request.

    Without HttpOnly one cross-site script is a stolen week-long session; without the path
    the token rides along on every catalogue call for no reason.
    """
    response = client.post(
        "/api/v1/auth/register", json={"email": "new@example.org", "password": PASSWORD}
    )

    cookie_header = response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "path=/api/v1/auth" in cookie_header


async def test_registering_a_taken_address_is_a_conflict(client: TestClient) -> None:
    """Two accounts on one address would make sign-in ambiguous."""
    response = client.post(
        "/api/v1/auth/register", json={"email": "student@example.org", "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "email_already_registered"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-address", "password": PASSWORD},
        {"email": "student2@example.org", "password": "short"},
        {"email": "", "password": PASSWORD},
    ],
)
async def test_malformed_registration_is_rejected(
    client: TestClient, payload: dict[str, str]
) -> None:
    """Validation happens before anything is written."""
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422


async def test_sign_in_with_a_wrong_password_is_unauthorized(client: TestClient) -> None:
    """The answer carries a code, not a sentence, and not which half was wrong."""
    response = client.post(
        "/api/v1/auth/login", json={"email": "student@example.org", "password": "nope-nope-nope"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"


async def test_unknown_address_answers_exactly_like_a_wrong_password(client: TestClient) -> None:
    """Identical bodies and status codes: the form must not confirm who is registered."""
    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": "student@example.org", "password": "nope-nope-nope"}
    )
    unknown_address = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.org", "password": "nope-nope-nope"}
    )

    assert wrong_password.status_code == unknown_address.status_code
    assert wrong_password.json() == unknown_address.json()


async def test_refresh_rotates_the_cookie(client: TestClient) -> None:
    """Every refresh replaces the cookie; the old value must not survive."""
    client.post("/api/v1/auth/login", json={"email": "student@example.org", "password": PASSWORD})
    first_cookie = client.cookies[REFRESH_COOKIE]

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert client.cookies[REFRESH_COOKIE] != first_cookie


async def test_replaying_an_old_cookie_is_refused(client: TestClient) -> None:
    """The point of rotation: a copied token stops working the moment the real one is used."""
    client.post("/api/v1/auth/login", json={"email": "student@example.org", "password": PASSWORD})
    stolen = client.cookies[REFRESH_COOKIE]
    client.post("/api/v1/auth/refresh")

    response = client.post("/api/v1/auth/refresh", cookies={REFRESH_COOKIE: stolen})

    assert response.status_code == 401
    assert response.json()["detail"] == "refresh_token_reused"


async def test_replay_also_ends_the_honest_session(
    client: TestClient, storage: tuple[FakeUserRepo, FakeRefreshTokenRepo]
) -> None:
    """
    After a replay both sessions end, not just the stolen one.

    At that moment the server cannot tell the thief from the user, so it ends everything
    and asks for a password again.
    """
    client.post("/api/v1/auth/login", json={"email": "student@example.org", "password": PASSWORD})
    stolen = client.cookies[REFRESH_COOKIE]
    client.post("/api/v1/auth/refresh")
    client.post("/api/v1/auth/refresh", cookies={REFRESH_COOKIE: stolen})

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert storage[1].live == []


async def test_refresh_without_a_cookie_is_unauthorized(client: TestClient) -> None:
    """A first visit has no session, and that is a 401, not a 500."""
    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


async def test_logout_makes_the_session_unusable(client: TestClient) -> None:
    """After signing out the refresh chain is dead even if the cookie is kept."""
    client.post("/api/v1/auth/login", json={"email": "student@example.org", "password": PASSWORD})
    cookie = client.cookies[REFRESH_COOKIE]

    assert client.post("/api/v1/auth/logout").status_code == 204

    response = client.post("/api/v1/auth/refresh", cookies={REFRESH_COOKIE: cookie})
    assert response.status_code == 401


async def test_me_requires_a_token(client: TestClient) -> None:
    """Closed by default: no token, no answer."""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


async def test_me_rejects_a_tampered_token(client: TestClient) -> None:
    """A forged signature is not a session."""
    signed_in = client.post(
        "/api/v1/auth/login", json={"email": "student@example.org", "password": PASSWORD}
    ).json()
    tampered = signed_in["access_token"][:-3] + "abc"

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"})

    assert response.status_code == 401


async def test_me_returns_the_account_behind_the_token(client: TestClient) -> None:
    """The signed-in account comes back without the password hash anywhere in the body."""
    signed_in = client.post(
        "/api/v1/auth/login", json={"email": "student@example.org", "password": PASSWORD}
    ).json()

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {signed_in['access_token']}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "student@example.org"
    assert "password" not in response.text


async def test_login_is_refused_after_too_many_attempts(client: TestClient) -> None:
    """
    Guessing has to stop being free.

    The allowance is per account as well as per host, so the tighter of the two is what a
    single attacker hits first.
    """
    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            json={"email": "student@example.org", "password": "wrong-password"},
        )

    refused = client.post(
        "/api/v1/auth/login", json={"email": "student@example.org", "password": PASSWORD}
    )

    assert refused.status_code == 429
    assert refused.json()["detail"] == "too_many_attempts"
    assert int(refused.headers["Retry-After"]) > 0


async def test_the_lock_follows_the_account_not_the_password(client: TestClient) -> None:
    """
    The correct password does not reset the counter.

    Otherwise an attacker who finally guesses right would never see a refusal, and the
    limit would only ever slow down the honest user who mistyped.
    """
    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            json={"email": "student@example.org", "password": "wrong-password"},
        )

    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "student@example.org", "password": PASSWORD}
        ).status_code
        == 429
    )


async def test_another_account_is_not_locked_out(client: TestClient) -> None:
    """One account under attack must not take the rest of the platform down with it."""
    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            json={"email": "student@example.org", "password": "wrong-password"},
        )

    other = client.post(
        "/api/v1/auth/login", json={"email": "someone-else@example.org", "password": PASSWORD}
    )

    assert other.status_code == 401


async def test_registration_is_rate_limited_too(client: TestClient) -> None:
    """Otherwise the sign-up form is a free way to mint accounts and probe addresses."""
    for index in range(5):
        client.post(
            "/api/v1/auth/register",
            json={"email": f"new{index}@example.org", "password": PASSWORD},
        )

    refused = client.post(
        "/api/v1/auth/register", json={"email": "new99@example.org", "password": PASSWORD}
    )

    assert refused.status_code == 429


async def test_a_readable_session_hint_is_left_beside_the_cookie(client: TestClient) -> None:
    """
    The page cannot see the HttpOnly refresh cookie, so it needs a hint that one exists.

    Without it the SPA has to try a refresh on every single load just to find out that the
    visitor was never signed in — a wasted round-trip and a 401 in everyone's console.
    """
    response = client.post(
        "/api/v1/auth/register", json={"email": "hint@example.org", "password": PASSWORD}
    )

    assert client.cookies[SESSION_HINT_COOKIE] == "1"
    assert "httponly" not in _cookie_attributes(response, SESSION_HINT_COOKIE)


async def test_the_hint_carries_no_authority(client: TestClient) -> None:
    """It says a session exists, nothing more: forging it must not authenticate anybody."""
    client.post("/api/v1/auth/register", json={"email": "hint2@example.org", "password": PASSWORD})
    token = client.cookies[REFRESH_COOKIE]
    client.cookies.clear()
    client.cookies.set(SESSION_HINT_COOKIE, "1")

    assert client.post("/api/v1/auth/refresh").status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert token  # the real credential was the one we threw away


async def test_logging_out_clears_the_hint(client: TestClient) -> None:
    """A stale hint would make every later page load try a refresh that cannot succeed."""
    client.post("/api/v1/auth/login", json={"email": "student@example.org", "password": PASSWORD})

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert client.cookies.get(SESSION_HINT_COOKIE) is None


def _cookie_attributes(response: Response, name: str) -> str:
    """The Set-Cookie line for one cookie, lower-cased, for attribute assertions."""
    for header in response.headers.get_list("set-cookie"):
        if header.startswith(f"{name}="):
            return str(header).lower()
    raise AssertionError(f"no Set-Cookie for {name}")
