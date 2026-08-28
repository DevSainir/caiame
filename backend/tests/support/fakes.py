"""
Hand-written stand-ins for repositories.

A MagicMock accepts any call and returns another mock, so a renamed repository method
leaves the test green while production breaks. These raise AttributeError instead.
"""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from models.accreditation import Accreditation
from models.base import uuid7
from models.course import Course
from models.enums import DifficultyLevel, UserRole
from models.refresh_token import RefreshToken
from models.specialization import Specialization
from models.user import User


class FakeCourseRepo:
    """In-memory course storage that applies the same filters the SQL does."""

    def __init__(self, courses: Sequence[Course]) -> None:
        self.courses = list(courses)
        self.calls: list[dict[str, object]] = []

    async def list_published(
        self,
        *,
        specialization_slug: str | None,
        accreditation_slug: str | None,
        difficulty: DifficultyLevel | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Course], int]:
        """Record the arguments and return the matching slice."""
        self.calls.append(
            {
                "specialization_slug": specialization_slug,
                "accreditation_slug": accreditation_slug,
                "difficulty": difficulty,
                "search": search,
                "limit": limit,
                "offset": offset,
            }
        )
        matched = [
            course
            for course in self.courses
            if (specialization_slug is None or course.specialization.slug == specialization_slug)
            and (
                accreditation_slug is None
                or (
                    course.accreditation is not None
                    and course.accreditation.slug == accreditation_slug
                )
            )
            and (difficulty is None or course.difficulty is difficulty)
            and (search is None or search.lower() in course.title.lower())
        ]
        return matched[offset : offset + limit], len(matched)


class FakeSpecializationRepo:
    """In-memory specialization storage."""

    def __init__(self, items: Sequence[Specialization]) -> None:
        self.items = list(items)

    async def list_active(self) -> Sequence[Specialization]:
        """Return every specialization."""
        return self.items


class FakeAccreditationRepo:
    """In-memory accreditation storage."""

    def __init__(self, items: Sequence[Accreditation]) -> None:
        self.items = list(items)

    async def list_active(self) -> Sequence[Accreditation]:
        """Return every accreditation scheme."""
        return self.items


class FakeUserRepo:
    """In-memory account storage."""

    def __init__(self, users: Sequence[User] = ()) -> None:
        self.users = list(users)

    async def get_by_email(self, email: str) -> User | None:
        """Find an account by address, matching the lower-cased storage convention."""
        wanted = email.lower()
        return next((user for user in self.users if user.email == wanted), None)

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find an account by id."""
        return next((user for user in self.users if user.id == user_id), None)

    async def create(
        self, *, email: str, password_hash: str, full_name: str, role: UserRole
    ) -> User:
        """Insert an account with an id already assigned."""
        user = User(
            id=uuid7(),
            email=email.lower(),
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        self.users.append(user)
        return user


class FakeRefreshTokenRepo:
    """In-memory refresh-token storage that keeps the same revocation semantics as SQL."""

    def __init__(self, tokens: Sequence[RefreshToken] = ()) -> None:
        self.tokens = list(tokens)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Find an issued token by its stored hash."""
        return next((token for token in self.tokens if token.token_hash == token_hash), None)

    async def create(
        self, *, user_id: UUID, token_hash: str, family_id: UUID, expires_at: datetime
    ) -> RefreshToken:
        """Store a newly issued token."""
        token = RefreshToken(
            id=uuid7(),
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        self.tokens.append(token)
        return token

    async def revoke(self, token: RefreshToken, *, at: datetime) -> None:
        """Mark one token as spent."""
        token.revoked_at = at

    async def revoke_family(self, family_id: UUID, *, at: datetime) -> None:
        """Revoke every live token of one login chain."""
        for token in self.tokens:
            if token.family_id == family_id and token.revoked_at is None:
                token.revoked_at = at

    @property
    def live(self) -> list[RefreshToken]:
        """Tokens that have not been revoked, which is what a session actually depends on."""
        return [token for token in self.tokens if token.revoked_at is None]


class FakeCounterStore:
    """In-memory fixed-window counters, with a switch to simulate the store being down."""

    def __init__(self, *, broken: bool = False) -> None:
        self.counts: dict[str, int] = {}
        self.broken = broken

    async def increment(self, key: str, *, window_seconds: int) -> tuple[int, int]:
        """Count one hit and report the running total with the seconds left."""
        if self.broken:
            raise ConnectionError("counter store is down")
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key], window_seconds
