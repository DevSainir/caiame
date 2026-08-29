"""
The half of the seeder that fills a course with content: outline, questions, reviews.

Split out of `seed.py` for size, not for layering — both halves are the same development
tool and talk to models directly. Everything here is deterministic: the random spread of
one student's progress is seeded from the course slug, so running the seeder twice gives
the same catalogue and a screenshot taken today still matches tomorrow.
"""

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from models.accreditation import Accreditation
from models.course import Course
from models.course_benefit import CourseBenefit
from models.course_question import CourseQuestion
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, UnitStatus
from models.review import Review
from models.specialization import Specialization
from models.unit_progress import UnitProgress
from models.user import User

KINDS = (
    ("modules", CourseUnitKind.MODULE),
    ("assignments", CourseUnitKind.ASSIGNMENT),
    ("tests", CourseUnitKind.TEST),
)
# How much of the plan the demo student has finished: from a quarter to three quarters.
# One unit after that is in progress and the rest are untouched — that is what real
# progress through a course looks like.
MIN_DONE_SHARE = 0.25
MAX_DONE_SHARE = 0.75
REVIEWS_PER_COURSE = 7
REVIEW_INTERVAL_DAYS = 37


async def seed_units(
    session: AsyncSession, courses: dict[str, Course], items: list[dict[str, Any]]
) -> int:
    """Insert the outline of every course: modules first, then assignments and tests."""
    created = 0
    for item in items:
        course = courses[str(item["slug"])]
        if await _has_rows(session, CourseUnit, course.id):
            continue
        for key, kind in KINDS:
            for position, unit in enumerate(item["syllabus"][key], start=1):
                session.add(
                    CourseUnit(
                        course_id=course.id,
                        kind=kind,
                        position=position,
                        title=str(unit["title"]),
                        summary=str(unit["summary"]),
                    )
                )
                created += 1
    await session.flush()
    return created


async def seed_questions(
    session: AsyncSession,
    courses: dict[str, Course],
    items: list[dict[str, Any]],
    facts: dict[str, dict[str, Any]],
) -> int:
    """
    Insert the discussion block: the same questions for every course, answered from its data.

    The answers are templates rather than fixed text on purpose — an answer that names the
    length or the audience must not be able to disagree with the course it stands under.
    """
    created = 0
    for slug, course in courses.items():
        if await _has_rows(session, CourseQuestion, course.id):
            continue
        for position, item in enumerate(items, start=1):
            session.add(
                CourseQuestion(
                    course_id=course.id,
                    position=position,
                    question=str(item["question"]),
                    answer=str(item["answer"]).format(**facts[slug]),
                )
            )
            created += 1
    return created


async def seed_benefits(
    session: AsyncSession,
    courses: dict[str, Course],
    items: list[dict[str, Any]],
    course_items: list[dict[str, Any]],
) -> int:
    """
    Insert the «why this course» blocks from the academy's own posters.

    Two of the five blocks are written per course and three are the same for the whole
    catalogue, so the shared ones are templates filled from the course they stand under.
    """
    created = 0
    by_slug = {str(item["slug"]): item for item in course_items}
    for slug, course in courses.items():
        if await _has_rows(session, CourseBenefit, course.id):
            continue
        fields = {
            "coverage": str(by_slug[slug]["summary"]),
            "teachers": str(by_slug[slug]["teachers"]),
        }
        for position, item in enumerate(items, start=1):
            session.add(
                CourseBenefit(
                    course_id=course.id,
                    position=position,
                    title=str(item["title"]),
                    text=str(item["text"]).format(**fields),
                )
            )
            created += 1
    return created


async def seed_review_authors(
    session: AsyncSession, items: list[dict[str, Any]], password: str
) -> list[User]:
    """Accounts to sign the demo reviews with; existing ones are reused."""
    authors: list[User] = []
    password_hash = hash_password(password)
    for item in items:
        email = str(item["email"])
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is None:
            existing = User(
                email=email, password_hash=password_hash, full_name=str(item["full_name"])
            )
            session.add(existing)
        authors.append(existing)
    await session.flush()
    return authors


async def seed_reviews(
    session: AsyncSession,
    courses: dict[str, Course],
    texts: list[dict[str, Any]],
    authors: list[User],
) -> int:
    """
    Sign a handful of reviews for every course.

    The pool of texts is shared and rotated by course, so no two courses open with the same
    review and every course has more of them than fits on one page.
    """
    created = 0
    now = datetime.now(UTC)
    for offset, course in enumerate(courses.values()):
        if await _has_rows(session, Review, course.id):
            continue
        for index in range(REVIEWS_PER_COURSE):
            item = texts[(offset * 3 + index) % len(texts)]
            session.add(
                Review(
                    course_id=course.id,
                    author_id=authors[(offset + index) % len(authors)].id,
                    rating=int(item["rating"]),
                    text=str(item["text"]),
                    # Spread over the past two years: all reviews dated today read as a
                    # seeded table, which is exactly what they would be.
                    created_at=now - timedelta(days=REVIEW_INTERVAL_DAYS * (index + offset)),
                )
            )
            created += 1
    return created


async def seed_progress(session: AsyncSession, student: User) -> int:
    """
    Give one demo student a believable amount of progress in every course.

    Progress runs along the plan instead of scattering across it: a finished last test
    above an untouched first module reads as a bug in the page rather than as a student
    who skipped ahead.
    """
    if await session.scalar(
        select(func.count(UnitProgress.id)).where(UnitProgress.user_id == student.id)
    ):
        return 0

    by_course: dict[Any, list[CourseUnit]] = {}
    for unit in (await session.scalars(select(CourseUnit))).all():
        by_course.setdefault(unit.course_id, []).append(unit)

    created = 0
    order = {kind: index for index, (_, kind) in enumerate(KINDS)}
    for course_id, units in by_course.items():
        # In the order the page shows them, so what is done is the start of the plan.
        units.sort(key=lambda unit: (order[unit.kind], unit.position))
        # Seeded from the course id, so the same database always looks the same.
        share = random.Random(str(course_id)).uniform(  # noqa: S311  # demo data, not crypto
            MIN_DONE_SHARE, MAX_DONE_SHARE
        )
        done = int(len(units) * share)
        for index, unit in enumerate(units[: done + 1]):
            status = UnitStatus.DONE if index < done else UnitStatus.IN_PROGRESS
            session.add(UnitProgress(user_id=student.id, unit_id=unit.id, status=status))
            created += 1
    return created


def course_facts(
    items: list[dict[str, Any]],
    specializations: dict[str, Specialization],
    accreditations: dict[str, Accreditation],
    audience_labels: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """
    Everything a question answer is allowed to say about the course it stands under.

    Assembled from the taxonomies the caller already holds rather than from the course
    relations: the seeder builds those objects in memory, and the relations are declared
    `lazy="raise"` precisely so a lazy load cannot happen outside a query.
    """
    facts = {}
    for item in items:
        syllabus = item["syllabus"]
        accreditation = accreditations[str(item["accreditation"])]
        specialization = specializations[str(item["specialization"])]
        facts[str(item["slug"])] = {
            "accreditation": accreditation.name,
            "hours": accreditation.short_code,
            "audience": audience_labels[str(specialization.audience)],
            "modules_count": len(syllabus["modules"]),
            "assignments_count": len(syllabus["assignments"]),
            "tests_count": len(syllabus["tests"]),
        }
    return facts


async def _has_rows(session: AsyncSession, model: type[Any], course_id: Any) -> bool:
    """Whether this course already carries rows of that kind — the seeder never doubles."""
    return bool(
        await session.scalar(select(func.count(model.id)).where(model.course_id == course_id))
    )
