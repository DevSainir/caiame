"""Builders for in-memory domain objects, so tests read as sentences and not as setup."""

from core.security import hash_password
from models.accreditation import Accreditation
from models.base import uuid7
from models.course import Course
from models.enums import CourseStatus, DifficultyLevel, UserRole
from models.specialization import Specialization
from models.user import User


def make_specialization(*, slug: str = "cardiology", name: str = "Cardiology") -> Specialization:
    """A medical field."""
    return Specialization(id=uuid7(), slug=slug, name=name, position=0)


def make_accreditation(
    *, slug: str = "nmo-36", name: str = "CME, 36 credits", short_code: str = "36"
) -> Accreditation:
    """A credit scheme."""
    return Accreditation(id=uuid7(), slug=slug, name=name, short_code=short_code, position=0)


def make_course(
    *,
    slug: str = "acute-coronary-syndrome",
    title: str = "Acute coronary syndrome",
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
    specialization: Specialization | None = None,
    accreditation: Accreditation | None = None,
) -> Course:
    """
    A published course with both taxonomies attached.

    Relations are assigned rather than loaded: the model declares `lazy="raise"`, so an
    unattached relation would explode in the serializer instead of returning a value.
    The id is set here too — the column default only fires on INSERT, and these objects
    never reach a database.
    """
    return Course(
        id=uuid7(),
        slug=slug,
        title=title,
        summary="A short summary.",
        description="A short summary.",
        cover_url=f"/covers/{slug}.jpg",
        status=CourseStatus.PUBLISHED,
        difficulty=difficulty,
        specialization=specialization or make_specialization(),
        accreditation=accreditation if accreditation is not None else make_accreditation(),
        price_minor=750_000,
        currency="KGS",
        credit_hours=36,
        duration_hours=40,
    )


def make_user(
    *,
    email: str = "student@example.org",
    password: str = "correct-horse-battery",
    role: UserRole = UserRole.STUDENT,
    is_active: bool = True,
) -> User:
    """An account with a real Argon2 hash, so password checks exercise the real path."""
    return User(
        id=uuid7(),
        email=email.lower(),
        password_hash=hash_password(password),
        full_name="",
        role=role,
        is_active=is_active,
    )
