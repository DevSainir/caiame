"""
The order of the course outline, against a real PostgreSQL.

The fake repository returns whatever list it was handed, so no amount of unit testing can
show what actually broke here: an ORDER BY that silently sorted by nothing. On the page it
looked like an assignment, two tests, another assignment — a plan nobody wrote.
"""

import asyncio
from uuid import UUID

import pytest
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from models.accreditation import Accreditation
from models.course import Course
from models.course_unit import CourseUnit
from models.enums import Audience, CourseStatus, CourseUnitKind
from models.specialization import Specialization
from repos.syllabus import SyllabusRepo

pytestmark = pytest.mark.integration

# Deliberately inserted out of order and with numbering that repeats across kinds: this is
# exactly the shape that hid the bug — every kind starts again from position 1.
UNITS = (
    (CourseUnitKind.TEST, 1),
    (CourseUnitKind.ASSIGNMENT, 2),
    (CourseUnitKind.MODULE, 2),
    (CourseUnitKind.TEST, 2),
    (CourseUnitKind.ASSIGNMENT, 1),
    (CourseUnitKind.MODULE, 1),
)


async def _seed_course(session_factory: async_sessionmaker) -> UUID:  # type: ignore[type-arg]
    """One published course with an outline of modules, assignments and tests."""
    async with session_factory() as session:
        specialization = Specialization(
            slug="therapy", name="Therapy", audience=Audience.DOCTOR, position=0
        )
        accreditation = Accreditation(
            slug="certification-72", name="Certified", short_code="72 h", position=0
        )
        session.add_all([specialization, accreditation])
        await session.flush()

        course = Course(
            slug="therapy",
            title="Therapy",
            summary="A course.",
            description="A course.",
            status=CourseStatus.PUBLISHED,
            specialization_id=specialization.id,
            accreditation_id=accreditation.id,
            price_minor=1_800_000,
            credit_hours=72,
            duration_hours=72,
        )
        session.add(course)
        await session.flush()

        for kind, position in UNITS:
            session.add(
                CourseUnit(
                    course_id=course.id,
                    kind=kind,
                    position=position,
                    title=f"{kind.value} {position}",
                    summary="",
                )
            )
        await session.commit()
        return course.id


async def _list_kinds(session_factory: async_sessionmaker, course_id: UUID) -> list[str]:  # type: ignore[type-arg]
    """The outline as the page receives it: kind of every line, in order."""
    async with session_factory() as session:
        units = await SyllabusRepo(session).list_units(course_id)
        return [f"{unit.kind.value}-{unit.position}" for unit in units]


def test_modules_come_first_then_assignments_then_tests(migrated_database: URL) -> None:
    """Kind decides the order, position decides it inside the kind — in that order."""
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        course_id = asyncio.run(_seed_course(factory))
        kinds = asyncio.run(_list_kinds(factory, course_id))
    finally:
        asyncio.run(engine.dispose())

    assert kinds == [
        "module-1",
        "module-2",
        "assignment-1",
        "assignment-2",
        "test-1",
        "test-2",
    ]
