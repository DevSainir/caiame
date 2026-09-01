"""The course outline and the progress derived from it."""

from collections.abc import Mapping, Sequence
from uuid import UUID

import pytest

from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, UnitStatus
from models.lesson import Lesson
from services.course import CourseNotFoundError
from services.syllabus import SyllabusService
from tests.support.factories import make_course, make_lesson, make_unit, make_user
from tests.support.fakes import (
    FakeBilling,
    FakeCourseRepo,
    FakeLessonRepo,
    FakeSyllabusRepo,
)


def _service(
    units: list[CourseUnit],
    unit_statuses: Mapping[UUID, str] | None = None,
    lessons: Sequence[Lesson] = (),
    lesson_statuses: Mapping[UUID, str] | None = None,
) -> SyllabusService:
    """A service over one published course, its outline and its lectures."""
    course = make_course(slug="therapy")
    for unit in units:
        unit.course_id = course.id
    return SyllabusService(
        course_repo=FakeCourseRepo([course]),
        syllabus_repo=FakeSyllabusRepo(units, dict(unit_statuses) if unit_statuses else None),
        lesson_repo=FakeLessonRepo(lessons, dict(lesson_statuses) if lesson_statuses else None),
        billing=FakeBilling(),
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

    syllabus = await service.get_syllabus(slug="therapy", viewer=None)

    assert [item.title for item in syllabus.modules] == ["Module"]
    assert [item.title for item in syllabus.activities] == ["Assignment", "Test"]


async def test_a_module_is_finished_when_its_lectures_are() -> None:
    """A module has no status of its own — it shows what its lectures add up to."""
    module = make_unit(title="Module", kind=CourseUnitKind.MODULE)
    lessons = [
        make_lesson(title=f"Lecture {index}", unit_id=module.id, position=index + 1)
        for index in range(2)
    ]
    service = _service(
        [module],
        lessons=lessons,
        lesson_statuses={lessons[0].id: UnitStatus.DONE, lessons[1].id: UnitStatus.DONE},
    )

    syllabus = await service.get_syllabus(slug="therapy", viewer=make_user())

    assert syllabus.modules[0].status is UnitStatus.DONE
    assert syllabus.progress_percent == 100


async def test_a_module_with_one_lecture_left_is_still_in_progress() -> None:
    """Two of three is not «done»: the row would claim a module nobody finished."""
    module = make_unit(title="Module", kind=CourseUnitKind.MODULE)
    lessons = [
        make_lesson(title=f"Lecture {index}", unit_id=module.id, position=index + 1)
        for index in range(3)
    ]
    service = _service(
        [module],
        lessons=lessons,
        lesson_statuses={lessons[0].id: UnitStatus.DONE, lessons[1].id: UnitStatus.DONE},
    )

    syllabus = await service.get_syllabus(slug="therapy", viewer=make_user())

    assert syllabus.modules[0].status is UnitStatus.IN_PROGRESS
    assert syllabus.progress_percent == 67


async def test_lectures_and_works_are_counted_together() -> None:
    """The percentage counts what a student does; a module is a container, not a deed."""
    module = make_unit(title="Module", kind=CourseUnitKind.MODULE)
    test = make_unit(title="Test", kind=CourseUnitKind.TEST)
    lesson = make_lesson(title="Lecture", unit_id=module.id)
    service = _service(
        [module, test],
        unit_statuses={test.id: UnitStatus.DONE},
        lessons=[lesson],
        lesson_statuses={lesson.id: UnitStatus.DONE},
    )

    syllabus = await service.get_syllabus(slug="therapy", viewer=make_user())

    assert syllabus.progress_percent == 100


async def test_an_optional_lecture_stays_out_of_the_denominator() -> None:
    """Extra reading must not hold a finished course at half for ever."""
    module = make_unit(title="Module", kind=CourseUnitKind.MODULE)
    required = make_lesson(title="Required", unit_id=module.id, position=1)
    optional = make_lesson(title="Bonus", unit_id=module.id, position=2, is_required=False)
    service = _service(
        [module], lessons=[required, optional], lesson_statuses={required.id: UnitStatus.DONE}
    )

    syllabus = await service.get_syllabus(slug="therapy", viewer=make_user())

    assert syllabus.progress_percent == 100


async def test_a_lecture_in_progress_is_not_a_finished_one() -> None:
    """Half a point for a started lecture is how a course reaches 100 % unfinished."""
    module = make_unit(title="Module", kind=CourseUnitKind.MODULE)
    lesson = make_lesson(title="Lecture", unit_id=module.id)
    service = _service(
        [module], lessons=[lesson], lesson_statuses={lesson.id: UnitStatus.IN_PROGRESS}
    )

    syllabus = await service.get_syllabus(slug="therapy", viewer=make_user())

    assert syllabus.progress_percent == 0


async def test_a_guest_sees_the_outline_with_nothing_started() -> None:
    """The outline is public; what somebody did with it is not, and is never asked for."""
    module = make_unit(title="Module", kind=CourseUnitKind.MODULE)
    lesson = make_lesson(title="Lecture", unit_id=module.id)
    service = _service([module], lessons=[lesson], lesson_statuses={lesson.id: UnitStatus.DONE})

    syllabus = await service.get_syllabus(slug="therapy", viewer=None)

    assert syllabus.modules[0].status is UnitStatus.NOT_STARTED
    assert syllabus.progress_percent == 0


async def test_an_unknown_course_has_no_outline() -> None:
    """An empty outline would read as a course without modules; this has to fail loudly."""
    service = SyllabusService(
        course_repo=FakeCourseRepo([]),
        syllabus_repo=FakeSyllabusRepo([]),
        lesson_repo=FakeLessonRepo(),
        billing=FakeBilling(),
    )

    with pytest.raises(CourseNotFoundError):
        await service.get_syllabus(slug="missing", viewer=None)
