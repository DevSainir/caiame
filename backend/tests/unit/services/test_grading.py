"""
Marking work by hand.

Three things here fail quietly rather than loudly: a reviewer marking their own work, a
second verdict overwriting the first, and an accepted piece of work that never closes the
line it belongs to.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import pytest

from models.assignment import Assignment
from models.base import uuid7
from models.course_unit import CourseUnit
from models.enrollment import Enrollment
from models.enums import CourseUnitKind, ReviewDecision, SubmissionStatus, UnitStatus
from models.media_file import MediaFile
from models.submission import Submission
from models.submission_review import SubmissionReview
from models.user import User
from schemas.assignment import ReviewIn
from services.grading import (
    AlreadyDecidedError,
    GradingService,
    SelfReviewError,
    SubmissionNotFoundError,
)
from tests.support.factories import make_unit, make_user


class FakeAssignmentRepo:
    """In-memory storage for work and the verdicts on it."""

    def __init__(
        self,
        *,
        submission: Submission,
        enrollment: Enrollment,
        student: User,
        unit: CourseUnit,
        assignment: Assignment,
    ) -> None:
        self.submissions = [submission]
        self.enrollment = enrollment
        self.student = student
        self.unit = unit
        self.assignment = assignment
        self.reviews: list[SubmissionReview] = []

    async def get_submission(self, submission_id: UUID) -> Submission | None:
        """One submission by id."""
        return next((item for item in self.submissions if item.id == submission_id), None)

    async def list_for_review(
        self, *, course_id: UUID | None, limit: int, offset: int
    ) -> Sequence[tuple[Submission, User, CourseUnit]]:
        """Everything waiting."""
        return [
            (item, self.student, self.unit)
            for item in self.submissions
            if item.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW)
        ]

    async def count_for_review(self, *, course_id: UUID | None) -> int:
        """How long the queue is."""
        return len(await self.list_for_review(course_id=course_id, limit=100, offset=0))

    async def list_files(self, submission_ids: Sequence[UUID]) -> Sequence[tuple[UUID, MediaFile]]:
        """No attachments in these cases."""
        return []

    async def list_reviews(
        self, submission_ids: Sequence[UUID]
    ) -> Sequence[tuple[SubmissionReview, str]]:
        """Reviews with the name of whoever wrote them."""
        return [
            (review, "Проверяющий")
            for review in self.reviews
            if review.submission_id in set(submission_ids)
        ]

    async def list_submissions(
        self, *, enrollment_id: UUID, assignment_id: UUID
    ) -> Sequence[Submission]:
        """Every attempt at one assignment."""
        return self.submissions

    async def add_review(self, review: SubmissionReview) -> SubmissionReview:
        """Store a verdict."""
        review.id = uuid7()
        self.reviews.append(review)
        return review

    async def owner_of(self, submission: Submission) -> tuple[Enrollment, User] | None:
        """Who sent this work in."""
        return self.enrollment, self.student

    async def set_status(
        self, submission: Submission, *, status: SubmissionStatus, at: datetime | None = None
    ) -> Submission:
        """Move the work to the next state."""
        submission.status = status
        return submission

    async def get_assignment(self, assignment_id: UUID) -> Assignment | None:
        """The assignment behind the work."""
        return self.assignment

    async def get_unit_of(self, assignment: Assignment) -> CourseUnit | None:
        """The line of the outline the assignment belongs to."""
        return self.unit


class FakeProgressRepo:
    """Where the course page reads whether a line is finished."""

    def __init__(self) -> None:
        self.marks: dict[UUID, UnitStatus] = {}

    async def mark_unit(self, *, user_id: UUID, unit_id: UUID, status: UnitStatus) -> None:
        """Record how far a student got in one line of the outline."""
        self.marks[unit_id] = status


class FakeSigner:
    """Links are not what these tests are about."""

    def playback_url(self, media: MediaFile) -> str:
        """A stand-in address."""
        return "https://storage.example/file"


def _service(
    *, status: SubmissionStatus = SubmissionStatus.SUBMITTED
) -> tuple[GradingService, Submission, User, FakeProgressRepo, FakeAssignmentRepo]:
    """A service over one piece of work sent in by one student."""
    student = make_user(email="student@example.org")
    unit = make_unit(title="Разбор случая", kind=CourseUnitKind.ASSIGNMENT)
    assignment = Assignment(id=uuid7(), unit_id=unit.id, description="", max_score=100)
    enrollment = Enrollment(
        id=uuid7(), user_id=student.id, course_id=unit.course_id, started_at=datetime.now(UTC)
    )
    submission = Submission(
        id=uuid7(),
        enrollment_id=enrollment.id,
        assignment_id=assignment.id,
        attempt_no=1,
        status=status,
        comment="Работа",
        submitted_at=datetime.now(UTC),
        is_late=False,
    )
    repo = FakeAssignmentRepo(
        submission=submission,
        enrollment=enrollment,
        student=student,
        unit=unit,
        assignment=assignment,
    )
    progress = FakeProgressRepo()
    service = GradingService(
        assignment_repo=repo, progress_repo=progress, media_service=FakeSigner()
    )
    return service, submission, student, progress, repo


async def test_accepted_work_closes_the_line_on_the_course_page() -> None:
    """The percentage on the course page is derived from marks like this one."""
    service, submission, _, progress, _ = _service()
    reviewer = make_user(email="teacher@example.org")

    await service.review(
        submission_id=submission.id,
        reviewer=reviewer,
        payload=ReviewIn(score=90, comment="Принято", decision=ReviewDecision.ACCEPTED),
    )

    assert list(progress.marks.values()) == [UnitStatus.DONE]


async def test_sending_back_for_revision_does_not_close_the_line() -> None:
    """The status does not roll back, because it never went up."""
    service, submission, _, progress, _ = _service()
    reviewer = make_user(email="teacher@example.org")

    result = await service.review(
        submission_id=submission.id,
        reviewer=reviewer,
        payload=ReviewIn(score=40, comment="Дополните", decision=ReviewDecision.NEEDS_REVISION),
    )

    assert result.status is SubmissionStatus.NEEDS_REVISION
    assert progress.marks == {}


async def test_nobody_marks_their_own_work() -> None:
    """
    An administrator taking a course is still a student in it.

    The check is on the study record behind the work, not on a role: the same person can be
    both, and the role says nothing about whose work this is.
    """
    service, submission, student, _, _ = _service()

    with pytest.raises(SelfReviewError):
        await service.review(
            submission_id=submission.id,
            reviewer=student,
            payload=ReviewIn(score=100, comment="own work", decision=ReviewDecision.ACCEPTED),
        )


async def test_a_marked_attempt_is_not_marked_again() -> None:
    """A second verdict would overwrite the first, and the student saw the first."""
    service, submission, _, _, _ = _service(status=SubmissionStatus.ACCEPTED)
    reviewer = make_user(email="teacher@example.org")

    with pytest.raises(AlreadyDecidedError):
        await service.review(
            submission_id=submission.id,
            reviewer=reviewer,
            payload=ReviewIn(score=10, comment="Передумал", decision=ReviewDecision.NEEDS_REVISION),
        )


async def test_the_queue_holds_only_what_is_waiting() -> None:
    """Marked work leaves the queue; otherwise it fills with everything ever sent."""
    service, submission, _, _, _ = _service()
    reviewer = make_user(email="teacher@example.org")
    assert (await service.queue(course_id=None, limit=20, offset=0)).total == 1

    await service.review(
        submission_id=submission.id,
        reviewer=reviewer,
        payload=ReviewIn(score=90, comment="Принято", decision=ReviewDecision.ACCEPTED),
    )

    assert (await service.queue(course_id=None, limit=20, offset=0)).total == 0


async def test_an_unknown_submission_is_not_found() -> None:
    """A guessed identifier says nothing about what exists."""
    service, _, _, _, _ = _service()

    with pytest.raises(SubmissionNotFoundError):
        await service.get_submission(uuid7())
