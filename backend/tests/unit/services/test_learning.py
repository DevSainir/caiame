"""
The lecture page: who may open it, and what it hands over when they may.

The outline above a lecture is a shop window and stays open to everybody; the lecture
itself is the thing being sold. These tests are about the line between the two.
"""

import pytest

from core.config import Settings
from models.base import uuid7
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, LessonKind, MediaStatus
from models.lesson import Lesson
from models.media_file import MediaFile
from services.billing import AccessRequiredError
from services.learning import LearningService
from services.media import MediaService
from tests.support.factories import make_course, make_lesson, make_unit, make_user
from tests.support.fakes import (
    FakeBilling,
    FakeCourseRepo,
    FakeEnrollmentRepo,
    FakeLessonRepo,
    FakeMediaRepo,
    FakeSyllabusRepo,
)
from tests.unit.services.test_media import MP4_HEAD, FakeStorage


def _media(*, status: MediaStatus) -> MediaFile:
    """One uploaded file in the state the case needs."""
    return MediaFile(
        id=uuid7(),
        bucket="caiame-private",
        key="lessons/one/lecture.mp4",
        is_public=False,
        original_name="lecture.mp4",
        content_type="video/mp4",
        size_bytes=1024,
        duration_seconds=1380,
        status=status,
    )


def _service(
    *,
    allowed: bool = True,
    media: MediaFile | None = None,
) -> tuple[LearningService, Lesson, CourseUnit]:
    """A service over one published course with one module and one lecture in it."""
    course = make_course(slug="therapy")
    unit = make_unit(title="Module one", kind=CourseUnitKind.MODULE)
    unit.course_id = course.id
    lesson = make_lesson(
        unit_id=unit.id, kind=LessonKind.VIDEO, media_file_id=media.id if media else None
    )
    storage = FakeStorage(head_bytes=MP4_HEAD)
    media_repo = FakeMediaRepo([media] if media else [])
    service = LearningService(
        course_repo=FakeCourseRepo([course]),
        unit_repo=FakeSyllabusRepo([unit]),
        lesson_repo=FakeLessonRepo([lesson]),
        media_repo=media_repo,
        media_service=MediaService(media_repo=media_repo, storage=storage, settings=Settings()),
        enrollment_repo=FakeEnrollmentRepo(),
        billing=FakeBilling(allowed=allowed),
    )
    return service, lesson, unit


async def test_a_student_without_access_cannot_open_a_lecture() -> None:
    """The refusal is the paywall: without it a signed-up account reads the whole course."""
    service, lesson, _ = _service(allowed=False)

    with pytest.raises(AccessRequiredError):
        await service.get_lesson(lesson_id=lesson.id, viewer=make_user())


async def test_a_student_without_access_cannot_mark_a_lecture_finished() -> None:
    """Writing progress for material one may not open is the same hole with a nicer name."""
    service, lesson, _ = _service(allowed=False)

    with pytest.raises(AccessRequiredError):
        await service.complete_lesson(lesson_id=lesson.id, viewer=make_user())


async def test_the_module_page_stays_open_and_says_the_material_is_not() -> None:
    """The list of lectures is what the course is selling; opening them is the question."""
    service, _, unit = _service(allowed=False)

    module = await service.get_module(unit_id=unit.id, viewer=make_user())

    assert module.has_access is False
    assert len(module.lessons) == 1


async def test_a_lecture_with_access_carries_a_link_to_its_file() -> None:
    """With the right in hand the page receives an address it did not have to build."""
    service, lesson, _ = _service(media=_media(status=MediaStatus.READY))

    detail = await service.get_lesson(lesson_id=lesson.id, viewer=make_user())

    assert detail.material_url is not None
    assert "lessons/one/lecture.mp4" in detail.material_url


async def test_an_unconfirmed_file_counts_as_no_material() -> None:
    """
    A lecture pointing at an upload that broke is worse than one that has nothing.

    The page then says the material is not there yet, instead of showing a player that
    fails on a file the storage never received.
    """
    service, lesson, _ = _service(media=_media(status=MediaStatus.PENDING))

    detail = await service.get_lesson(lesson_id=lesson.id, viewer=make_user())

    assert detail.material_url is None


async def test_opening_a_lecture_enrols_the_student() -> None:
    """
    Enrolment happens at the first lecture somebody is entitled to open.

    It is what the «continue» button reads later, and it is never deleted — access can end,
    the record and the progress under it stay.
    """
    service, lesson, _ = _service()
    student = make_user()

    await service.get_lesson(lesson_id=lesson.id, viewer=student)

    records = service.enrollment_repo.records  # type: ignore[attr-defined]
    assert list(records.values()) == [lesson.id]
