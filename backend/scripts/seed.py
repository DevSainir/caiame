"""
Fill an empty database with a catalogue that looks like the real thing.

Development tool, not application code: it talks to models directly instead of going
through the layers, because there is no request and no user here. Running it twice is
safe — every row is matched by its natural key first.

The catalogue text lives in `seed_data.json` rather than in this module. It is content,
not code, and keeping it out of the source keeps every Cyrillic-confusable lint rule on.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from seed_learning import (
    course_facts,
    seed_benefits,
    seed_lessons,
    seed_progress,
    seed_questions,
    seed_quizzes,
    seed_review_authors,
    seed_reviews,
    seed_units,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.db import session_factory
from core.security import hash_password
from models.accreditation import Accreditation
from models.course import Course
from models.enums import Audience, CourseStatus, UserRole
from models.registry import Base  # noqa: F401  # imports every table before the mapper runs
from models.specialization import Specialization
from models.user import User

DATA_PATH = Path(__file__).with_name("seed_data.json")
# Development credentials, for a local database only.
DEV_PASSWORD = "caiame-dev-2026"  # noqa: S105  # seed account password, local use only


def load_data() -> dict[str, Any]:
    """
    Read the catalogue content that ships with the repository.

    Typed loosely on purpose: the file holds lists of rows and one lookup table, and a
    precise type here would be a second copy of the schema that nothing validates.
    """
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


async def seed_specializations(
    session: AsyncSession, items: list[dict[str, Any]]
) -> dict[str, Specialization]:
    """Insert the specializations, keeping the order they are shown in."""
    result: dict[str, Specialization] = {}
    for position, item in enumerate(items):
        slug = str(item["slug"])
        existing = await session.scalar(select(Specialization).where(Specialization.slug == slug))
        if existing is None:
            existing = Specialization(
                slug=slug,
                name=str(item["name"]),
                audience=Audience(item["audience"]),
                position=position,
            )
            session.add(existing)
        result[slug] = existing
    await session.flush()
    return result


async def seed_accreditations(
    session: AsyncSession, items: list[dict[str, Any]]
) -> dict[str, Accreditation]:
    """Insert the credit schemes a course can be accredited under."""
    result: dict[str, Accreditation] = {}
    for position, item in enumerate(items):
        slug = str(item["slug"])
        existing = await session.scalar(select(Accreditation).where(Accreditation.slug == slug))
        if existing is None:
            existing = Accreditation(
                slug=slug,
                name=str(item["name"]),
                short_code=str(item["short_code"]),
                position=position,
            )
            session.add(existing)
        result[slug] = existing
    await session.flush()
    return result


async def seed_courses(
    session: AsyncSession,
    items: list[dict[str, Any]],
    specializations: dict[str, Specialization],
    accreditations: dict[str, Accreditation],
) -> dict[str, Course]:
    """Insert the published catalogue and hand the rows back, keyed by slug."""
    result: dict[str, Course] = {}
    for item in items:
        slug = str(item["slug"])
        existing = await session.scalar(select(Course).where(Course.slug == slug))
        if existing is not None:
            # The cover is refreshed even on a course that is already there: it is the one
            # field that gets replaced after the fact — a photograph swapped for another, or
            # for a generated card — and a seeder that only ever inserts leaves the old file
            # on the live site with nothing to say why.
            existing.cover_url = str(item["cover"])
            result[slug] = existing
            continue
        course = Course(
            slug=slug,
            title=str(item["title"]),
            summary=str(item["summary"]),
            # Paragraphs in the file, one blank line between them in the column: the
            # course page splits them back apart, and JSON has no multi-line string.
            description="\n\n".join(str(text) for text in item["description"]),
            # A photograph where the academy has one, a generated card where it does not:
            # the path is written in the data file, not guessed from the slug.
            cover_url=str(item["cover"]),
            status=CourseStatus.PUBLISHED,
            specialization_id=specializations[str(item["specialization"])].id,
            accreditation_id=accreditations[str(item["accreditation"])].id,
            price_minor=int(item["price_minor"]),
            currency="KGS",
            credit_hours=int(item["credit_hours"]),
            duration_hours=int(item["duration_hours"]),
        )
        session.add(course)
        result[slug] = course
    await session.flush()
    return result


async def seed_users(session: AsyncSession, items: list[dict[str, Any]]) -> dict[str, User]:
    """Insert one account per role, so the access ladder can be exercised locally."""
    result: dict[str, User] = {}
    password_hash = hash_password(DEV_PASSWORD)
    for item in items:
        email = str(item["email"])
        role = UserRole(item["role"])
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is None:
            existing = User(
                email=email,
                password_hash=password_hash,
                full_name=str(item["full_name"]),
                role=role,
            )
            session.add(existing)
        result[str(role)] = existing
    await session.flush()
    return result


async def main() -> None:
    """
    Seed every table the course pages read.

    Demo accounts are created only outside production. Their password is committed to this
    repository, so seeding them on a public server would put an administrator account with a
    published password on the internet. Reviews and progress go with them: both need a
    person behind them, and inventing students on a live server is worse than an empty
    block that says there are no reviews yet.
    """
    data = load_data()
    is_production = get_settings().environment == "production"
    async with session_factory() as session:
        specializations = await seed_specializations(session, data["specializations"])
        accreditations = await seed_accreditations(session, data["accreditations"])
        courses = await seed_courses(session, data["courses"], specializations, accreditations)
        units = await seed_units(session, courses, data["courses"])
        facts = course_facts(
            data["courses"], specializations, accreditations, data["audience_labels"]
        )
        questions = await seed_questions(session, courses, data["questions"], facts)
        benefits = await seed_benefits(session, courses, data["benefits"], data["courses"])
        lessons = await seed_lessons(session, courses, data["lesson_templates"])
        quizzes = await seed_quizzes(
            session, courses, data["quiz_template"], facts, data["courses"]
        )

        reviews = progress = 0
        users: dict[str, User] = {}
        if not is_production:
            users = await seed_users(session, data["users"])
            authors = await seed_review_authors(session, data["review_authors"], DEV_PASSWORD)
            reviews = await seed_reviews(session, courses, data["review_texts"], authors)
            progress = await seed_progress(session, users["student"])
        await session.commit()

    demo = (
        "demo content skipped in production"
        if is_production
        else f"{len(users)} users, {reviews} new reviews, {progress} progress rows"
    )
    print(
        f"seeded: {len(specializations)} specializations, {len(accreditations)} accreditations, "
        f"{len(courses)} courses, {units} new units, {questions} new questions, "
        f"{benefits} new benefits, {lessons} new lessons, {quizzes} new questions, {demo}"
    )


if __name__ == "__main__":
    asyncio.run(main())
