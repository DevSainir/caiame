"""
The lecture page: who may open it, and what it hands over when they may.

The outline above a lecture is a shop window and stays open to everybody; the lecture
itself is the thing being sold. These tests are about the line between the two.
"""

import pytest

from core.config import Settings
from models.base import uuid7
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, LessonKind, MediaStatus, UnitStatus
from models.lesson import Lesson
from models.media_file import MediaFile
from services.billing import AccessRequiredError
from services.learning import LearningService, completion_is_the_students_to_declare
from services.media import MediaService
from services.rate_limit import RateLimitService
from tests.support.factories import make_course, make_lesson, make_unit, make_user
from tests.support.fakes import (
    FakeBilling,
    FakeCompletion,
    FakeCounterStore,
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
        duration_seconds=0,
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
    lesson_repo = FakeLessonRepo([lesson])
    service = LearningService(
        course_repo=FakeCourseRepo([course]),
        unit_repo=FakeSyllabusRepo([unit]),
        lesson_repo=lesson_repo,
        media_repo=media_repo,
        playback_repo=lesson_repo,
        media_service=MediaService(
            media_repo=media_repo,
            storage=storage,
            settings=Settings(),
            rate_limiter=RateLimitService(store=FakeCounterStore()),
        ),
        enrollment_repo=FakeEnrollmentRepo(),
        completion=FakeCompletion(),
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


async def test_dragging_to_the_end_does_not_finish_the_lecture() -> None:
    """
    The trap this whole feature exists for.

    The position says the player is at the last second; nothing was played. A lecture that
    closes on that is a lecture nobody watched, and the certificate behind it means nothing.
    """
    media = _media(status=MediaStatus.READY)
    media.duration_seconds = 600
    service, lesson, _ = _service(media=media)
    student = make_user()

    result = await service.report_playback(
        lesson_id=lesson.id, viewer=student, position_sec=599, delta_sec=1
    )

    assert result.status is not UnitStatus.DONE
    assert result.watched_seconds == 1


async def test_watching_most_of_it_finishes_the_lecture() -> None:
    """Ninety per cent counts: titles and goodbyes at the end are not watched by everybody."""
    media = _media(status=MediaStatus.READY)
    media.duration_seconds = 100
    service, lesson, _ = _service(media=media)
    student = make_user()

    for _ in range(9):
        result = await service.report_playback(
            lesson_id=lesson.id, viewer=student, position_sec=90, delta_sec=10
        )

    assert result.status is UnitStatus.DONE


async def test_an_invented_report_is_capped_rather_than_believed() -> None:
    """
    A client claiming an hour between two events gets the ceiling and no error.

    Refusing would break a player on a slow connection; believing would hand out completion
    to anybody willing to edit one number.
    """
    media = _media(status=MediaStatus.READY)
    media.duration_seconds = 600
    service, lesson, _ = _service(media=media)
    student = make_user()

    result = await service.report_playback(
        lesson_id=lesson.id, viewer=student, position_sec=30, delta_sec=3600
    )

    assert result.watched_seconds == 60
    assert result.status is not UnitStatus.DONE


async def test_the_position_is_remembered_so_the_lecture_reopens_where_it_stopped() -> None:
    """The other half of the pair: position moves anywhere, including backwards."""
    media = _media(status=MediaStatus.READY)
    media.duration_seconds = 600
    service, lesson, _ = _service(media=media)
    student = make_user()

    await service.report_playback(
        lesson_id=lesson.id, viewer=student, position_sec=120, delta_sec=30
    )
    result = await service.report_playback(
        lesson_id=lesson.id, viewer=student, position_sec=45, delta_sec=5
    )

    assert result.last_position_sec == 45
    assert result.watched_seconds == 35


async def test_a_lecture_without_a_known_length_does_not_finish_itself() -> None:
    """A file whose length nobody knows cannot be judged watched — and must not be guessed."""
    service, lesson, _ = _service(media=_media(status=MediaStatus.READY))
    student = make_user()

    result = await service.report_playback(
        lesson_id=lesson.id, viewer=student, position_sec=10, delta_sec=60
    )

    assert result.status is not UnitStatus.DONE


async def test_playback_of_a_closed_course_is_refused() -> None:
    """Reporting playback is reading the material, so the same right decides."""
    service, lesson, _ = _service(allowed=False)

    with pytest.raises(AccessRequiredError):
        await service.report_playback(
            lesson_id=lesson.id, viewer=make_user(), position_sec=1, delta_sec=1
        )


def test_a_handout_is_closed_by_the_student() -> None:
    """Nothing can be observed about reading a file; the button is the only evidence."""
    assert completion_is_the_students_to_declare(LessonKind.PDF, duration_seconds=0) is True


def test_a_video_of_known_length_is_closed_by_watching_it() -> None:
    """Otherwise the button would close a lecture nobody played."""
    assert completion_is_the_students_to_declare(LessonKind.VIDEO, duration_seconds=600) is False


def test_a_video_nobody_could_measure_falls_back_to_the_student() -> None:
    """
    The length is read by the browser that uploaded the file, and an undecodable codec
    leaves a zero. Measured against zero the lecture never finishes — and neither does the
    module, nor the course, and nobody is told why.
    """
    assert completion_is_the_students_to_declare(LessonKind.VIDEO, duration_seconds=0) is True
