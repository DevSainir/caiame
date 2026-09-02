"""Builders for in-memory domain objects, so tests read as sentences and not as setup."""

from datetime import UTC, datetime
from uuid import UUID

from core.security import hash_password
from models.accreditation import Accreditation
from models.base import uuid7
from models.course import Course
from models.course_benefit import CourseBenefit
from models.course_question import CourseQuestion
from models.course_unit import CourseUnit
from models.enums import Audience, CourseStatus, CourseUnitKind, LessonKind, UserRole
from models.lesson import Lesson
from models.review import Review
from models.specialization import Specialization
from models.user import User


def make_specialization(
    *,
    slug: str = "therapy",
    name: str = "Therapy",
    audience: Audience = Audience.DOCTOR,
) -> Specialization:
    """A field of practice."""
    return Specialization(id=uuid7(), slug=slug, name=name, audience=audience, position=0)


def make_accreditation(
    *, slug: str = "certification-72", name: str = "Certified, 72 hours", short_code: str = "72 h"
) -> Accreditation:
    """A credit scheme."""
    return Accreditation(id=uuid7(), slug=slug, name=name, short_code=short_code, position=0)


def make_course(
    *,
    slug: str = "therapy",
    title: str = "Therapy",
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
    specialization = specialization or make_specialization()
    accreditation = accreditation if accreditation is not None else make_accreditation()
    return Course(
        id=uuid7(),
        # Both the relation and the key it is written through: the key is filled in on
        # flush, and these objects never reach a database — without it a course looks like
        # one nobody assigned to a field of practice.
        specialization_id=specialization.id,
        accreditation_id=accreditation.id if accreditation is not None else None,
        slug=slug,
        title=title,
        summary="A short summary.",
        description="A short summary.",
        cover_url=f"/covers/{slug}.jpg",
        status=CourseStatus.PUBLISHED,
        specialization=specialization,
        accreditation=accreditation,
        price_minor=750_000,
        currency="KGS",
        credit_hours=72,
        duration_hours=72,
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


def make_unit(
    *,
    title: str = "Module one",
    kind: CourseUnitKind = CourseUnitKind.MODULE,
    position: int = 1,
    course_id: UUID | None = None,
) -> CourseUnit:
    """One line of a course outline."""
    return CourseUnit(
        id=uuid7(),
        course_id=course_id or uuid7(),
        kind=kind,
        position=position,
        title=title,
        summary="One line about it.",
    )


def make_review(*, rating: int = 5, author: User | None = None, text: str = "Good.") -> Review:
    """A review with its author already attached, since the relation raises on lazy load."""
    review = Review(
        id=uuid7(),
        course_id=uuid7(),
        author_id=uuid7(),
        rating=rating,
        text=text,
        author=author or make_user(email="reviewer@example.org"),
    )
    review.created_at = datetime(2026, 8, 1, tzinfo=UTC)
    return review


def make_question(
    *, question: str = "How long is it?", answer: str = "72 hours."
) -> CourseQuestion:
    """One question of the discussion block."""
    return CourseQuestion(
        id=uuid7(), course_id=uuid7(), position=1, question=question, answer=answer
    )


def make_benefit(*, title: str = "Convenient format", text: str = "Study online.") -> CourseBenefit:
    """One reason to take the course."""
    return CourseBenefit(id=uuid7(), course_id=uuid7(), position=1, title=title, text=text)


def make_lesson(
    *,
    title: str = "Lecture one",
    unit_id: UUID | None = None,
    position: int = 1,
    kind: LessonKind = LessonKind.VIDEO,
    is_required: bool = True,
    media_file_id: UUID | None = None,
) -> Lesson:
    """One lecture inside a module."""
    return Lesson(
        id=uuid7(),
        unit_id=unit_id or uuid7(),
        position=position,
        title=title,
        description="One line about it.",
        kind=kind,
        duration_minutes=23,
        media_file_id=media_file_id,
        is_required=is_required,
    )
