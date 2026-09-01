"""
The session rules: rotation, replay detection and the two ways sign-in can fail.

Every test here guards something that fails silently in production — a refresh chain that
keeps working after a token leaks, or an error message that tells an attacker which
addresses exist.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from core.security import hash_refresh_token, verify_password
from models.refresh_token import RefreshToken
from models.user import User
from services.auth import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    TokenReuseDetectedError,
)
from services.rate_limit import RateLimitService
from tests.support.factories import make_user
from tests.support.fakes import FakeCounterStore, FakeRefreshTokenRepo, FakeUserRepo

CLIENT_IP = "203.0.113.10"


def build_service(
    users: Sequence[User] = (), tokens: Sequence[RefreshToken] = ()
) -> tuple[AuthService, FakeUserRepo, FakeRefreshTokenRepo]:
    """Wire the service to in-memory storage and hand back both repositories to inspect."""
    user_repo = FakeUserRepo(users)
    refresh_repo = FakeRefreshTokenRepo(tokens)
    service = AuthService(
        user_repo=user_repo,
        refresh_repo=refresh_repo,
        rate_limiter=RateLimitService(store=FakeCounterStore()),
    )
    return service, user_repo, refresh_repo


async def test_refresh_spends_the_old_token_and_issues_a_new_one() -> None:
    """Rotation: after a refresh exactly one token of the family is still usable."""
    user = make_user()
    service, _, refresh_repo = build_service([user])
    first = await service.login(
        email=user.email, password="correct-horse-battery", client_ip=CLIENT_IP
    )

    second = await service.refresh(first.refresh_token)

    assert second.refresh_token != first.refresh_token
    assert [token.token_hash for token in refresh_repo.live] == [
        hash_refresh_token(second.refresh_token)
    ]


async def test_rotated_token_stays_in_the_same_family() -> None:
    """A refresh continues the login chain instead of starting a new one."""
    user = make_user()
    service, _, refresh_repo = build_service([user])
    first = await service.login(
        email=user.email, password="correct-horse-battery", client_ip=CLIENT_IP
    )

    await service.refresh(first.refresh_token)

    assert len({token.family_id for token in refresh_repo.tokens}) == 1


async def test_replaying_a_spent_token_kills_the_whole_family() -> None:
    """
    A second use of an already-rotated token can only mean a copy leaked.

    The stolen copy and the honest client are indistinguishable at that point, so both
    sessions end and the user signs in again. Leaving the family alive is how a stolen
    token keeps working for a week.
    """
    user = make_user()
    service, _, refresh_repo = build_service([user])
    first = await service.login(
        email=user.email, password="correct-horse-battery", client_ip=CLIENT_IP
    )
    await service.refresh(first.refresh_token)

    with pytest.raises(TokenReuseDetectedError):
        await service.refresh(first.refresh_token)

    assert refresh_repo.live == []


async def test_expired_refresh_token_is_refused() -> None:
    """An expired token is not a valid one, however untouched it is."""
    user = make_user()
    service, _, refresh_repo = build_service([user])
    issued = await service.login(
        email=user.email, password="correct-horse-battery", client_ip=CLIENT_IP
    )
    refresh_repo.tokens[0].expires_at = datetime.now(UTC) - timedelta(seconds=1)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(issued.refresh_token)


async def test_unknown_refresh_token_is_refused() -> None:
    """A token that was never issued cannot mint a session."""
    service, _, _ = build_service()

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh("not-a-token-we-ever-issued")


async def test_refresh_token_is_stored_hashed() -> None:
    """A database dump must not be a bundle of working sessions."""
    user = make_user()
    service, _, refresh_repo = build_service([user])

    issued = await service.login(
        email=user.email, password="correct-horse-battery", client_ip=CLIENT_IP
    )

    stored = refresh_repo.tokens[0].token_hash
    assert stored != issued.refresh_token
    assert stored == hash_refresh_token(issued.refresh_token)


async def test_deactivated_account_cannot_refresh() -> None:
    """Turning an account off ends its sessions at the next refresh, without a job to run."""
    user = make_user()
    service, _, _ = build_service([user])
    issued = await service.login(
        email=user.email, password="correct-horse-battery", client_ip=CLIENT_IP
    )
    user.is_active = False

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(issued.refresh_token)


async def test_logout_ends_every_token_of_the_session() -> None:
    """Signing out has to outlive the token in hand, or an older copy resurrects the session."""
    user = make_user()
    service, _, refresh_repo = build_service([user])
    issued = await service.login(
        email=user.email, password="correct-horse-battery", client_ip=CLIENT_IP
    )

    await service.logout(issued.refresh_token)

    assert refresh_repo.live == []


async def test_wrong_password_and_unknown_address_fail_the_same_way() -> None:
    """
    Both branches raise the same error.

    A different error — or a visibly faster one — turns the sign-in form into a query for
    "is this address registered", which is the first step of credential stuffing.
    """
    user = make_user(email="known@example.org")
    service, _, _ = build_service([user])

    with pytest.raises(InvalidCredentialsError):
        await service.login(
            email="known@example.org", password="wrong-password", client_ip=CLIENT_IP
        )
    with pytest.raises(InvalidCredentialsError):
        await service.login(
            email="unknown@example.org", password="wrong-password", client_ip=CLIENT_IP
        )


async def test_inactive_account_cannot_sign_in() -> None:
    """A disabled account fails like a wrong password, not with a distinct message."""
    user = make_user(is_active=False)
    service, _, _ = build_service([user])

    with pytest.raises(InvalidCredentialsError):
        await service.login(email=user.email, password="correct-horse-battery", client_ip=CLIENT_IP)


async def test_registration_refuses_a_taken_address() -> None:
    """Two accounts on one address would make sign-in ambiguous."""
    user = make_user(email="taken@example.org")
    service, _, _ = build_service([user])

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(
            email="TAKEN@example.org", password="another-password", client_ip=CLIENT_IP
        )


async def test_registration_normalises_the_address() -> None:
    """Case and stray spaces must not create a second account for the same person."""
    service, user_repo, _ = build_service()

    await service.register(
        email="  Student@Example.ORG ", password="correct-horse-battery", client_ip=CLIENT_IP
    )

    assert user_repo.users[0].email == "student@example.org"


async def test_new_account_is_always_a_student() -> None:
    """The role is assigned by the service; an endpoint that accepts one hands out admin."""
    service, user_repo, _ = build_service()

    issued = await service.register(
        email="new@example.org", password="correct-horse-battery", client_ip=CLIENT_IP
    )

    assert issued.session.user.role.value == "student"
    assert user_repo.users[0].role.value == "student"


async def test_changing_the_password_needs_the_current_one() -> None:
    """
    A session left open on somebody else's machine must not be enough to take the account.

    This is the only thing standing between a borrowed laptop and a stolen account, so the
    refusal is checked before anything else about the feature.
    """
    user = make_user(email="student@example.org", password="correct-horse-battery")
    service = AuthService(
        user_repo=FakeUserRepo([user]),
        refresh_repo=FakeRefreshTokenRepo(),
        rate_limiter=RateLimitService(store=FakeCounterStore()),
    )
    before = user.password_hash

    with pytest.raises(InvalidCredentialsError):
        await service.change_password(
            user=user, current_password="not-the-password", new_password="new-password-here"
        )

    assert user.password_hash == before


async def test_a_password_change_ends_every_other_session() -> None:
    """
    A refresh token outlives the password it was issued under.

    Without this, changing the password of an account somebody else is signed into leaves
    them signed in for another week — which is the one thing the change was for.
    """
    user = make_user(email="student@example.org", password="correct-horse-battery")
    refresh_repo = FakeRefreshTokenRepo()
    service = AuthService(
        user_repo=FakeUserRepo([user]),
        refresh_repo=refresh_repo,
        rate_limiter=RateLimitService(store=FakeCounterStore()),
    )
    await service.login(
        email="student@example.org", password="correct-horse-battery", client_ip="1.1.1.1"
    )
    await service.login(
        email="student@example.org", password="correct-horse-battery", client_ip="2.2.2.2"
    )
    assert len(refresh_repo.live) == 2

    await service.change_password(
        user=user,
        current_password="correct-horse-battery",
        new_password="a-brand-new-password",
    )

    # Ровно одна живая сессия — та, что выдана в ответе: человек, сменивший пароль,
    # не должен оказаться выброшенным из системы этим же действием.
    assert len(refresh_repo.live) == 1


async def test_the_new_password_works_and_the_old_one_does_not() -> None:
    """The point of the whole feature, stated as the two facts that make it true."""
    user = make_user(email="student@example.org", password="correct-horse-battery")
    service = AuthService(
        user_repo=FakeUserRepo([user]),
        refresh_repo=FakeRefreshTokenRepo(),
        rate_limiter=RateLimitService(store=FakeCounterStore()),
    )

    await service.change_password(
        user=user,
        current_password="correct-horse-battery",
        new_password="a-brand-new-password",
    )

    assert verify_password("a-brand-new-password", user.password_hash)
    assert not verify_password("correct-horse-battery", user.password_hash)
