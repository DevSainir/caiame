"""
The course itself: created, described, published, deleted.

Two rules here are worth a test each. A new course is a draft — a course that appeared in
the catalogue by the act of being created would be published by a typo. And a course is
deleted only while nobody has seen it: published courses and courses with students hold
somebody else's history under them.
"""

from collections.abc import Sequence
from uuid import UUID

import pytest

from models.base import uuid7
from models.course import Course
from models.enums import CourseStatus
from schemas.admin import CourseIn
from services.administration import (
    AdministrationService,
    CourseInUseError,
    CourseNotFoundForAdminError,
)
from tests.support.factories import make_course
from tests.support.fakes import FakeAdminRepo, FakeLessonRepo, FakeMediaRepo, FakeSyllabusRepo


def _service(
    courses: Sequence[Course] = (), students: dict[UUID, int] | None = None
) -> tuple[AdministrationService, FakeAdminRepo]:
    """A service over the courses handed in, with the counts the screen shows."""
    repo = FakeAdminRepo(list(courses), students=students or {})
    service = AdministrationService(
        admin_repo=repo,
        unit_repo=FakeSyllabusRepo([]),
        lesson_repo=FakeLessonRepo([]),
        media_repo=FakeMediaRepo(),
    )
    return service, repo


def _payload(title: str = "Повышение квалификации по терапии") -> CourseIn:
    """The form as it arrives from the administration screen."""
    return CourseIn(title=title, summary="", description="", specialization_id=uuid7())


async def test_a_new_course_is_a_draft() -> None:
    """Appearing in the catalogue is a decision, never a side effect of being created."""
    service, _ = _service()

    created = await service.create_course(_payload())

    assert created.status is CourseStatus.DRAFT


async def test_the_address_is_made_from_the_title_in_latin() -> None:
    """A Cyrillic address survives copying badly, and the title is what people type."""
    service, _ = _service()

    created = await service.create_course(_payload("Повышение квалификации по терапии"))

    assert created.slug.isascii()
    assert created.slug


async def test_two_courses_with_one_title_do_not_share_an_address() -> None:
    """The second one gets the next free number instead of overwriting the first."""
    service, _ = _service()

    first = await service.create_course(_payload())
    second = await service.create_course(_payload())

    assert first.slug != second.slug


async def test_renaming_a_course_leaves_its_address_alone() -> None:
    """Links to it are already in people's hands, and they must not break on a retitle."""
    service, _ = _service()
    created = await service.create_course(_payload())

    changed = await service.update_course(
        course_id=created.id, payload=_payload("Терапия: обновлённый цикл")
    )

    assert changed.slug == created.slug
    assert changed.title == "Терапия: обновлённый цикл"


async def test_a_draft_nobody_takes_is_deleted() -> None:
    """Nothing is lost with it — that is what makes deleting it allowed at all."""
    draft = make_course(slug="draft")
    draft.status = CourseStatus.DRAFT
    service, repo = _service([draft])

    await service.delete_course(draft.id)

    assert repo.courses == []


async def test_a_published_course_is_not_deleted() -> None:
    """It has been in front of people; the way to retire it is to unpublish it."""
    published = make_course(slug="therapy")
    service, repo = _service([published])

    with pytest.raises(CourseInUseError):
        await service.delete_course(published.id)

    assert repo.courses == [published]


async def test_a_course_with_students_is_not_deleted_even_as_a_draft() -> None:
    """Their progress hangs under it, and deleting the course takes the progress with it."""
    draft = make_course(slug="draft")
    draft.status = CourseStatus.DRAFT
    service, _ = _service([draft], students={draft.id: 1})

    with pytest.raises(CourseInUseError):
        await service.delete_course(draft.id)


async def test_publishing_and_unpublishing_answer_with_the_course() -> None:
    """The screen re-reads the programme itself; the status is what changed here."""
    draft = make_course(slug="draft")
    draft.status = CourseStatus.DRAFT
    service, _ = _service([draft])

    published = await service.set_status(course_id=draft.id, status=CourseStatus.PUBLISHED)
    hidden = await service.set_status(course_id=draft.id, status=CourseStatus.DRAFT)

    assert published.status is CourseStatus.PUBLISHED
    assert hidden.status is CourseStatus.DRAFT


async def test_a_guessed_course_id_is_not_found() -> None:
    """The refusal says nothing about what exists, drafts included."""
    service, _ = _service()

    with pytest.raises(CourseNotFoundForAdminError):
        await service.get_course_detail(uuid7())
