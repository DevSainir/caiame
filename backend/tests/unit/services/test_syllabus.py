"""The course outline and the progress derived from it."""

from collections.abc import Mapping
from uuid import UUID

import pytest

from models.base import uuid7
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, UnitStatus
from services.course import CourseNotFoundError
from services.syllabus import SyllabusService
from tests.support.factories import make_course, make_unit
from tests.support.fakes import FakeCourseRepo, FakeSyllabusRepo


def _service(
    units: list[CourseUnit], statuses: Mapping[UUID, str] | None = None
) -> SyllabusService:
    """A service over one published course and the outline handed in."""
    course = make_course(slug="therapy")
    for unit in units:
        unit.course_id = course.id
    return SyllabusService(
        course_repo=FakeCourseRepo([course]),
        syllabus_repo=FakeSyllabusRepo(units, dict(statuses) if statuses else None),
    )


async def test_modules_and_works_land_in_their_own_lists() -> None:
    """The page draws two cards, so the outline arrives already split into two."""
    service = _service(
        [
            make_unit(title="Module", kind=CourseUnitKind.MODULE),
            make_unit(title="Assignment", kind=CourseUnitKind.ASSIGNMENT),
            make_unit(title="Test", kind=CourseUnitKind.TEST),
        ]
    )

    syllabus = await service.get_syllabus(slug="therapy", user_id=None)

    assert [item.title for item in syllabus.modules] == ["Module"]
    assert [item.title for item in syllabus.activities] == ["Assignment", "Test"]


async def test_progress_is_counted_from_the_facts() -> None:
    """Two of four units done is 50%, and the number exists nowhere else to disagree with."""
    units = [make_unit(title=f"Unit {index}", position=index) for index in range(4)]
    statuses = {
        units[0].id: UnitStatus.DONE,
        units[1].id: UnitStatus.DONE,
        units[2].id: UnitStatus.IN_PROGRESS,
    }
    service = _service(units, statuses)

    syllabus = await service.get_syllabus(slug="therapy", user_id=uuid7())

    assert syllabus.progress_percent == 50


async def test_a_unit_in_progress_is_not_a_finished_one() -> None:
    """Counting half a point for a started unit is how a course reaches 100% unfinished."""
    units = [make_unit(title="Only one")]
    service = _service(units, {units[0].id: UnitStatus.IN_PROGRESS})

    syllabus = await service.get_syllabus(slug="therapy", user_id=uuid7())

    assert syllabus.progress_percent == 0


async def test_a_guest_sees_the_outline_with_nothing_started() -> None:
    """The outline is public; what somebody did with it is not, and is never asked for."""
    units = [make_unit(title="Module")]
    service = _service(units, {units[0].id: UnitStatus.DONE})

    syllabus = await service.get_syllabus(slug="therapy", user_id=None)

    assert syllabus.modules[0].status is UnitStatus.NOT_STARTED
    assert syllabus.progress_percent == 0


async def test_an_unknown_course_has_no_outline() -> None:
    """An empty outline would read as a course without modules; this has to fail loudly."""
    service = SyllabusService(course_repo=FakeCourseRepo([]), syllabus_repo=FakeSyllabusRepo([]))

    with pytest.raises(CourseNotFoundError):
        await service.get_syllabus(slug="missing", user_id=None)
