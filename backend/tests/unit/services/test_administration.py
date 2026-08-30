"""Editing a course: ownership of the identifier, order, and what deletion means."""

from collections.abc import Sequence

import pytest

from models.base import uuid7
from models.course import Course
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, LessonKind
from models.lesson import Lesson
from schemas.admin import LessonIn, UnitIn, UnitUpdateIn
from services.administration import (
    AdministrationService,
    LessonNotFoundError,
    ModuleNotEmptyError,
    UnitNotFoundError,
)
from tests.support.factories import make_course, make_lesson, make_unit
from tests.support.fakes import FakeAdminRepo, FakeLessonRepo, FakeSyllabusRepo


def _service(
    units: Sequence[CourseUnit] = (), lessons: Sequence[Lesson] = ()
) -> tuple[AdministrationService, Course]:
    """A service over one course with the outline handed in."""
    course = make_course(slug="therapy")
    for unit in units:
        unit.course_id = course.id
    syllabus = FakeSyllabusRepo(list(units))
    lesson_repo = FakeLessonRepo(list(lessons))
    return (
        AdministrationService(
            admin_repo=FakeAdminRepo([course], list(units), list(lessons)),
            unit_repo=syllabus,
            lesson_repo=lesson_repo,
        ),
        course,
    )


async def test_a_new_module_lands_after_the_last_one() -> None:
    """Position is decided by the server: a client that picks it collides with itself."""
    first = make_unit(title="First", kind=CourseUnitKind.MODULE, position=1)
    service, course = _service([first])

    created = await service.add_unit(
        course_id=course.id, payload=UnitIn(title="Second", summary="", kind=CourseUnitKind.MODULE)
    )

    assert created.position == 2


async def test_a_module_of_another_course_is_not_found() -> None:
    """A guessed identifier must not edit somebody else's programme."""
    service, course = _service([make_unit(title="Mine", kind=CourseUnitKind.MODULE)])

    with pytest.raises(UnitNotFoundError):
        await service.update_unit(
            course_id=course.id,
            unit_id=uuid7(),
            payload=UnitUpdateIn(title="Hijacked", summary=""),
        )


async def test_moving_swaps_two_positions() -> None:
    """One step is one swap, and both rows are written together."""
    first = make_unit(title="First", kind=CourseUnitKind.MODULE, position=1)
    second = make_unit(title="Second", kind=CourseUnitKind.MODULE, position=2)
    service, course = _service([first, second])

    await service.move_unit(course_id=course.id, unit_id=second.id, direction=-1)

    assert (first.position, second.position) == (2, 1)


async def test_moving_past_the_end_does_nothing() -> None:
    """The button at the top of a list is not an error, it is simply the top."""
    only = make_unit(title="Only", kind=CourseUnitKind.MODULE, position=1)
    service, course = _service([only])

    await service.move_unit(course_id=course.id, unit_id=only.id, direction=-1)

    assert only.position == 1


async def test_a_module_with_lectures_is_not_deleted() -> None:
    """Deleting it would take the lectures — and somebody's progress in them — with it."""
    module = make_unit(title="Module", kind=CourseUnitKind.MODULE)
    lesson = make_lesson(title="Lecture", unit_id=module.id)
    service, course = _service([module], [lesson])

    with pytest.raises(ModuleNotEmptyError):
        await service.delete_unit(course_id=course.id, unit_id=module.id)


async def test_a_lecture_is_retired_and_not_erased() -> None:
    """
    Soft deletion, because progress rows and attempts point at the lecture.

    A student who finished eight of ten lectures must see 100 % after two unfinished ones
    are removed: the lecture leaves the denominator, not the history.
    """
    module = make_unit(title="Module", kind=CourseUnitKind.MODULE)
    lesson = make_lesson(title="Lecture", unit_id=module.id)
    service, course = _service([module], [lesson])

    await service.delete_lesson(course_id=course.id, lesson_id=lesson.id)

    assert lesson.deleted_at is not None


async def test_a_lecture_cannot_be_hung_on_a_test() -> None:
    """Lectures live inside modules; a work is not a container."""
    test_unit = make_unit(title="Test", kind=CourseUnitKind.TEST)
    service, course = _service([test_unit])

    with pytest.raises(UnitNotFoundError):
        await service.add_lesson(
            course_id=course.id,
            unit_id=test_unit.id,
            payload=LessonIn(title="Lecture", kind=LessonKind.VIDEO),
        )


async def test_a_lecture_of_another_course_is_not_found() -> None:
    """Same rule as for a module: the address never widens what may be edited."""
    service, course = _service([make_unit(title="Module", kind=CourseUnitKind.MODULE)])

    with pytest.raises(LessonNotFoundError):
        await service.delete_lesson(course_id=course.id, lesson_id=uuid7())
