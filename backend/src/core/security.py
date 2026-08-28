import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from core.config import get_settings

_hasher = PasswordHasher()
_settings = get_settings()

# Hashed once at import and compared against on a missing account, so answering "no such
# user" costs the same wall-clock time as answering "wrong password".
_DUMMY_HASH = _hasher.hash("timing-equalizer")


def hash_password(password: str) -> str:
    """Hash a password with Argon2id, so a leaked dump does not hand over accounts."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against its hash, returning False instead of raising on mismatch."""
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def waste_password_comparison() -> None:
    """
    Burn the same time a real comparison costs.

    Called when the address is unknown: without it, response time tells an attacker which
    addresses are registered, which is exactly the list a credential-stuffing run wants.
    """
    verify_password("timing-equalizer-probe", _DUMMY_HASH)


def create_access_token(user_id: UUID) -> str:
    """Issue a short-lived bearer token carrying the user id and nothing else sensitive."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=_settings.access_token_ttl_minutes)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Verify and decode an access token.

    Raises `jwt.InvalidTokenError` on anything wrong — expiry, signature, tampering — so
    the caller has one failure to handle rather than four.
    """
    payload: dict[str, Any] = jwt.decode(
        token, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm]
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload


def generate_refresh_token() -> str:
    """Create an opaque refresh token with 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for storage.

    SHA-256 rather than Argon2 on purpose: the token is random, not chosen by a human, so
    there is no dictionary to slow down — and every refresh would pay the Argon2 cost.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
