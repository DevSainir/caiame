from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from core.config import get_settings
from core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    waste_password_comparison,
)
from models.base import uuid7
from models.enums import UserRole
from models.refresh_token import RefreshToken
from models.user import User
from schemas.auth import SessionOut
from schemas.user import UserOut
from services.rate_limit import RateLimitService

_settings = get_settings()


class AuthError(Exception):
    """Base for every refusal this service can produce."""


class EmailAlreadyRegisteredError(AuthError):
    """The address already has an account. The router turns this into a 409."""


class InvalidCredentialsError(AuthError):
    """Wrong address or wrong password — deliberately indistinguishable."""


class InvalidRefreshTokenError(AuthError):
    """The presented refresh token is unknown, expired, or its account is gone."""


class TokenReuseDetectedError(AuthError):
    """A revoked refresh token was presented again, so the whole family was terminated."""


class UserReader(Protocol):
    """What authentication needs from user storage."""

    async def get_by_email(self, email: str) -> User | None:
        """Find an account by address."""
        ...

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find an account by id."""
        ...

    async def create(
        self, *, email: str, password_hash: str, full_name: str, role: UserRole
    ) -> User:
        """Insert an account."""
        ...


class RefreshTokenWriter(Protocol):
    """What authentication needs from refresh-token storage."""

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Find an issued token by its stored hash."""
        ...

    async def create(
        self, *, user_id: UUID, token_hash: str, family_id: UUID, expires_at: datetime
    ) -> RefreshToken:
        """Store a newly issued token."""
        ...

    async def revoke(self, token: RefreshToken, *, at: datetime) -> None:
        """Mark one token as spent."""
        ...

    async def revoke_family(self, family_id: UUID, *, at: datetime) -> None:
        """Revoke every live token of one login chain."""
        ...


@dataclass(frozen=True)
class IssuedSession:
    """
    A freshly issued pair.

    The refresh token leaves the service as a raw value exactly once — the router puts it
    straight into an HttpOnly cookie. Only its hash reaches the database.
    """

    session: SessionOut
    refresh_token: str
    refresh_expires_at: datetime


class AuthService:
    """Registration, sign-in and the rotating refresh chain."""

    def __init__(
        self,
        *,
        user_repo: UserReader,
        refresh_repo: RefreshTokenWriter,
        rate_limiter: RateLimitService,
    ) -> None:
        self.user_repo = user_repo
        self.refresh_repo = refresh_repo
        self.rate_limiter = rate_limiter

    async def register(self, *, email: str, password: str, client_ip: str) -> IssuedSession:
        """
        Create a student account and sign it in.

        The role is not accepted from the request: an endpoint that takes a role is an
        endpoint that hands out the admin role to whoever asks for it.
        """
        await self.rate_limiter.hit(
            f"register:ip:{client_ip}",
            limit=_settings.register_attempts_per_ip,
            window_seconds=_settings.register_window_seconds,
        )
        normalized = email.strip().lower()
        if await self.user_repo.get_by_email(normalized) is not None:
            raise EmailAlreadyRegisteredError(normalized)
        user = await self.user_repo.create(
            email=normalized,
            password_hash=hash_password(password),
            full_name="",
            role=UserRole.STUDENT,
        )
        return await self._issue(user, family_id=uuid7())

    async def login(self, *, email: str, password: str, client_ip: str) -> IssuedSession:
        """
        Sign an existing account in.

        Both failure branches cost the same time and raise the same error: a faster "no
        such user" would turn this endpoint into a list of registered addresses.
        """
        normalized = email.strip().lower()
        # Two counters, because one is not enough on its own: the address counter stops a
        # botnet grinding one account from many hosts, and the address counter alone would
        # let one host walk through a list of accounts.
        await self.rate_limiter.hit(
            f"login:ip:{client_ip}",
            limit=_settings.login_attempts_per_ip,
            window_seconds=_settings.login_window_seconds,
        )
        await self.rate_limiter.hit(
            f"login:account:{normalized}",
            limit=_settings.login_attempts_per_account,
            window_seconds=_settings.login_window_seconds,
        )

        user = await self.user_repo.get_by_email(normalized)
        if user is None:
            waste_password_comparison()
            raise InvalidCredentialsError
        if not verify_password(password, user.password_hash) or not user.is_active:
            raise InvalidCredentialsError
        return await self._issue(user, family_id=uuid7())

    async def refresh(self, raw_token: str) -> IssuedSession:
        """
        Exchange a refresh token for a new pair, spending the old one.

        Rotation is what makes theft detectable: only the newest token of a family is live,
        so a second use of an already-spent token means a copy is circulating.
        """
        now = datetime.now(UTC)
        stored = await self.refresh_repo.get_by_hash(hash_refresh_token(raw_token))
        if stored is None:
            raise InvalidRefreshTokenError("unknown token")

        if stored.revoked_at is not None:
            await self.refresh_repo.revoke_family(stored.family_id, at=now)
            raise TokenReuseDetectedError("refresh token replayed")

        if stored.expires_at <= now:
            raise InvalidRefreshTokenError("expired token")

        user = await self.user_repo.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError("account unavailable")

        await self.refresh_repo.revoke(stored, at=now)
        return await self._issue(user, family_id=stored.family_id)

    async def logout(self, raw_token: str | None) -> None:
        """
        End the session the cookie belongs to.

        Revokes the whole family rather than the single row: the caller is saying "this
        device is done", and a stale token from the same chain must not outlive it.
        """
        if not raw_token:
            return
        stored = await self.refresh_repo.get_by_hash(hash_refresh_token(raw_token))
        if stored is None:
            return
        await self.refresh_repo.revoke_family(stored.family_id, at=datetime.now(UTC))

    async def _issue(self, user: User, *, family_id: UUID) -> IssuedSession:
        """Mint an access token and the next refresh token of the family."""
        raw_refresh = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=_settings.refresh_token_ttl_days)
        await self.refresh_repo.create(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            family_id=family_id,
            expires_at=expires_at,
        )
        return IssuedSession(
            session=SessionOut(
                access_token=create_access_token(user.id),
                expires_in=_settings.access_token_ttl_minutes * 60,
                user=UserOut.model_validate(user),
            ),
            refresh_token=raw_refresh,
            refresh_expires_at=expires_at,
        )
