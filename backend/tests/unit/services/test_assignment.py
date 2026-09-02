"""
The student's side of an assignment.

Four rules here fail quietly rather than loudly: a second attempt started while the first
one is still in the queue, a file that belongs to somebody else, an upload that never
finished, and late work in an assignment that does not take it.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from models.assignment import Assignment
from models.base import uuid7
from models.course import Course
from models.course_unit import CourseUnit
from models.enrollment import Enrollment
from models.enums import CourseUnitKind, MediaStatus, SubmissionStatus
from models.media_file import MediaFile
from models.submission import Submission
from models.submission_review import SubmissionReview
from models.user import User
from schemas.assignment import SubmissionIn
from services.assignment import (
    AssignmentNotFoundError,
    AssignmentService,
    AttachmentRejectedError,
    DeadlinePassedError,
    SubmissionNotAllowedError,
)
from services.billing import AccessRequiredError
from tests.support.factories import make_course, make_unit, make_user
from tests.support.fakes import FakeBilling, FakeMediaRepo


class FakeUnitRepo:
    """The one line of the outline these tests know about."""

    def __init__(self, unit: CourseUnit) -> None:
        self.unit = unit

    async def get_unit(self, unit_id: UUID) -> CourseUnit | None:
        """The line by its id."""
        return self.unit if self.unit.id == unit_id else None


class FakeCourseRepo:
    """A course that is either published or, for a draft, simply absent."""

    def __init__(self, course: Course | None) -> None:
        self.course = course

    async def get_published_by_id(self, course_id: UUID) -> Course | None:
        """The course, if it is in the catalogue at all."""
        if self.course is None or self.course.id != course_id:
            return None
        return self.course


class FakeAssignmentRepo:
    """In-memory attempts at one assignment."""

    def __init__(self, *, assignment: Assignment | None = None) -> None:
        self.assignment = assignment
        self.submissions: list[Submission] = []
        self.created: list[Assignment] = []

    async def get_by_unit(self, unit_id: UUID) -> Assignment | None:
        """The assignment behind the line, while it exists."""
        return self.assignment

    async def create(self, assignment: Assignment) -> Assignment:
        """
        Bring one into being on first use.

        Column defaults are applied by hand: they fire on INSERT, and these objects never
        reach a database — without this the freshly made assignment has no maximum score.
        """
        assignment.id = uuid7()
        assignment.max_score = 100
        assignment.allow_late = True
        self.assignment = assignment
        self.created.append(assignment)
        return assignment

    async def list_submissions(
        self, *, enrollment_id: UUID, assignment_id: UUID
    ) -> Sequence[Submission]:
        """Every attempt, oldest first."""
        return self.submissions

    async def next_attempt_no(self, *, enrollment_id: UUID, assignment_id: UUID) -> int:
        """The number the next attempt gets."""
        return len(self.submissions) + 1

    async def add_submission(self, submission: Submission, media_ids: Sequence[UUID]) -> Submission:
        """Store an attempt with the files sent along with it."""
        submission.id = uuid7()
        self.submissions.append(submission)
        return submission

    async def list_files(self, submission_ids: Sequence[UUID]) -> Sequence[tuple[UUID, MediaFile]]:
        """No attachments matter to these cases."""
        return []

    async def list_reviews(
        self, submission_ids: Sequence[UUID]
    ) -> Sequence[tuple[SubmissionReview, str]]:
        """Nobody has looked at this work yet."""
        return []


class FakeEnrolments:
    """Study records that appear on the way in, as they do in the real repository."""

    def __init__(self) -> None:
        self.records: dict[tuple[UUID, UUID], Enrollment] = {}

    async def ensure(self, *, user_id: UUID, course_id: UUID, last_lesson_id: UUID | None) -> None:
        """Enrol a student who is not enrolled yet."""
        self.records.setdefault(
            (user_id, course_id),
            Enrollment(
                id=uuid7(),
                user_id=user_id,
                course_id=course_id,
                started_at=datetime.now(UTC),
            ),
        )

    async def get(self, *, user_id: UUID, course_id: UUID) -> Enrollment | None:
        """The record of one student in one course."""
        return self.records.get((user_id, course_id))


class FakeSigner:
    """Links are not what these tests are about."""

    def playback_url(self, media: MediaFile) -> str:
        """A stand-in address."""
        return "https://storage.example/file"


def make_media(*, owner: User, status: MediaStatus = MediaStatus.READY) -> MediaFile:
    """An uploaded file, ready or still on its way."""
    return MediaFile(
        id=uuid7(),
        bucket="private",
        key=f"submissions/{uuid7()}",
        is_public=False,
        original_name="work.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        status=status,
        uploaded_by_id=owner.id,
    )


def _service(
    *,
    student: User | None = None,
    published: bool = True,
    kind: CourseUnitKind = CourseUnitKind.ASSIGNMENT,
    deadline_at: datetime | None = None,
    allow_late: bool = True,
    allowed: bool = True,
    files: Sequence[MediaFile] = (),
) -> tuple[AssignmentService, CourseUnit, User, FakeAssignmentRepo, FakeBilling]:
    """A service over one assignment of one published course."""
    student = student or make_user(email="student@example.org")
    course = make_course(slug="ophthalmology", title="Офтальмология")
    unit = make_unit(title="Разбор случая", kind=kind, course_id=course.id)
    assignment = Assignment(
        id=uuid7(),
        unit_id=unit.id,
        description="Опишите случай",
        max_score=100,
        deadline_at=deadline_at,
        allow_late=allow_late,
    )
    repo = FakeAssignmentRepo(assignment=assignment)
    billing = FakeBilling(allowed=allowed)
    service = AssignmentService(
        unit_repo=FakeUnitRepo(unit),
        course_repo=FakeCourseRepo(course if published else None),
        assignment_repo=repo,
        enrollment_repo=FakeEnrolments(),
        media_repo=FakeMediaRepo(files),
        media_service=FakeSigner(),
        billing=billing,
    )
    return service, unit, student, repo, billing


async def test_the_page_opens_and_the_first_attempt_is_allowed() -> None:
    """Nothing sent in yet means the form is open, not that something is missing."""
    service, unit, student, _, _ = _service()

    page = await service.get_page(unit_id=unit.id, viewer=student)

    assert page.can_submit is True
    assert page.submissions == []


async def test_work_waiting_in_the_queue_blocks_a_second_attempt() -> None:
    """
    A second attempt would not be looked at sooner and pushes somebody else down the queue.

    It is also the case where the student sees two versions of their own work and cannot
    tell which one is being marked.
    """
    service, unit, student, _, _ = _service()
    await service.submit(unit_id=unit.id, viewer=student, payload=SubmissionIn(comment="Первая"))

    with pytest.raises(SubmissionNotAllowedError):
        await service.submit(unit_id=unit.id, viewer=student, payload=SubmissionIn(comment="Ещё"))


async def test_work_sent_back_for_revision_can_be_sent_again() -> None:
    """That is what «revision» means; refusing here would close the only way forward."""
    service, unit, student, repo, _ = _service()
    await service.submit(unit_id=unit.id, viewer=student, payload=SubmissionIn(comment="Первая"))
    repo.submissions[-1].status = SubmissionStatus.NEEDS_REVISION

    page = await service.submit(
        unit_id=unit.id, viewer=student, payload=SubmissionIn(comment="Исправил")
    )

    assert [item.attempt_no for item in page.submissions] == [1, 2]


async def test_accepted_work_is_not_sent_again() -> None:
    """The verdict is in; another attempt would ask for a second one."""
    service, unit, student, repo, _ = _service()
    await service.submit(unit_id=unit.id, viewer=student, payload=SubmissionIn(comment="Первая"))
    repo.submissions[-1].status = SubmissionStatus.ACCEPTED

    with pytest.raises(SubmissionNotAllowedError):
        await service.submit(unit_id=unit.id, viewer=student, payload=SubmissionIn(comment="Ещё"))


async def test_somebody_elses_file_does_not_attach_to_my_work() -> None:
    """
    An identifier is not a proof of ownership.

    Without this check a guessed id puts another student's file into my work, and the
    reviewer reads it as mine.
    """
    stranger = make_user(email="stranger@example.org")
    theirs = make_media(owner=stranger)
    service, unit, student, _, _ = _service(files=[theirs])

    with pytest.raises(AttachmentRejectedError):
        await service.submit(
            unit_id=unit.id, viewer=student, payload=SubmissionIn(media_ids=[theirs.id])
        )


async def test_an_unfinished_upload_does_not_attach() -> None:
    """A pending row means the object may not be in storage at all."""
    student = make_user(email="student@example.org")
    half_way = make_media(owner=student, status=MediaStatus.PENDING)
    service, unit, student, _, _ = _service(student=student, files=[half_way])

    with pytest.raises(AttachmentRejectedError):
        await service.submit(
            unit_id=unit.id, viewer=student, payload=SubmissionIn(media_ids=[half_way.id])
        )


async def test_late_work_is_marked_late_but_taken() -> None:
    """Lateness is a fact for whoever marks the work, not a refusal by the system."""
    yesterday = datetime.now(UTC) - timedelta(days=1)
    service, unit, student, _, _ = _service(deadline_at=yesterday, allow_late=True)

    page = await service.submit(
        unit_id=unit.id, viewer=student, payload=SubmissionIn(comment="Опоздал")
    )

    assert page.submissions[-1].is_late is True


async def test_an_assignment_that_refuses_late_work_refuses_it() -> None:
    """When the deadline is hard, it has to be hard on the server."""
    yesterday = datetime.now(UTC) - timedelta(days=1)
    service, unit, student, _, _ = _service(deadline_at=yesterday, allow_late=False)

    with pytest.raises(DeadlinePassedError):
        await service.submit(
            unit_id=unit.id, viewer=student, payload=SubmissionIn(comment="Поздно")
        )


async def test_access_is_asked_about_before_anything_is_shown() -> None:
    """The assignment is course material: a closed course does not show it either."""
    service, unit, student, _, billing = _service(allowed=False)

    with pytest.raises(AccessRequiredError):
        await service.get_page(unit_id=unit.id, viewer=student)

    assert billing.asked == [unit.course_id]


async def test_an_assignment_of_a_draft_course_does_not_exist() -> None:
    """A draft says nothing about itself, not even that it is a draft."""
    service, unit, student, _, _ = _service(published=False)

    with pytest.raises(AssignmentNotFoundError):
        await service.get_page(unit_id=unit.id, viewer=student)


async def test_a_lecture_is_not_an_assignment() -> None:
    """The same address space holds both; the kind is what separates them."""
    service, unit, student, _, _ = _service(kind=CourseUnitKind.MODULE)

    with pytest.raises(AssignmentNotFoundError):
        await service.get_page(unit_id=unit.id, viewer=student)


async def test_the_assignment_appears_on_first_use() -> None:
    """A line that already says «assignment» does not wait for somebody to press a button."""
    service, unit, student, repo, _ = _service()
    repo.assignment = None

    page = await service.get_page(unit_id=unit.id, viewer=student)

    assert len(repo.created) == 1
    assert page.title == unit.title
