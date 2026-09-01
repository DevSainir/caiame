"""
The student's side of an assignment: what to do, and what has been sent in so far.

The rule that shapes this module is that nothing is ever overwritten. Work sent back for
revision becomes the next attempt, with its own number, its own files and its own review.
The student has to be able to see what they were told last time and the reviewer has to be
able to see what changed; one rewrite destroys both.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from models.assignment import Assignment
from models.course import Course
from models.course_unit import CourseUnit
from models.enrollment import Enrollment
from models.enums import CourseUnitKind, MediaStatus, SubmissionStatus
from models.media_file import MediaFile
from models.submission import Submission
from models.submission_review import SubmissionReview
from models.user import User
from schemas.assignment import (
    AssignmentOut,
    AttachmentOut,
    ReviewOut,
    SubmissionIn,
    SubmissionOut,
)

# States in which the student is waiting for somebody else, and a second attempt would only
# add noise to the queue.
PENDING_STATES = (SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW)


class AssignmentNotFoundError(Exception):
    """No such assignment in a published course."""


class SubmissionNotAllowedError(Exception):
    """There is already an attempt waiting, or the work has been accepted."""


class AttachmentRejectedError(Exception):
    """A file that is not this student's, or one whose upload never finished."""


class DeadlinePassedError(Exception):
    """The assignment refuses late work and the deadline is behind."""


class UnitReader(Protocol):
    """The outline, as this service reads it."""

    async def get_unit(self, unit_id: UUID) -> CourseUnit | None: ...


class CourseReader(Protocol):
    """Published courses only: an assignment of a draft course does not exist for students."""

    async def get_published_by_id(self, course_id: UUID) -> Course | None: ...


class EnrolmentStore(Protocol):
    """Where the study record lives."""

    async def ensure(self, *, user_id: UUID, course_id: UUID, last_lesson_id: UUID | None) -> None:
        """Enrol a student if they are not enrolled yet."""
        ...

    async def get(self, *, user_id: UUID, course_id: UUID) -> Enrollment | None:
        """The study record of one student in one course."""
        ...


class AssignmentStore(Protocol):
    """Everything the assignment page needs from storage."""

    async def get_by_unit(self, unit_id: UUID) -> Assignment | None: ...
    async def create(self, assignment: Assignment) -> Assignment: ...
    async def list_submissions(
        self, *, enrollment_id: UUID, assignment_id: UUID
    ) -> Sequence[Submission]: ...
    async def next_attempt_no(self, *, enrollment_id: UUID, assignment_id: UUID) -> int: ...
    async def add_submission(
        self, submission: Submission, media_ids: Sequence[UUID]
    ) -> Submission: ...
    async def list_files(
        self, submission_ids: Sequence[UUID]
    ) -> Sequence[tuple[UUID, MediaFile]]: ...
    async def list_reviews(
        self, submission_ids: Sequence[UUID]
    ) -> Sequence[tuple[SubmissionReview, str]]: ...


class MediaStore(Protocol):
    """Uploaded files, for checking that an attachment is real and belongs to the sender."""

    async def get(self, media_id: UUID) -> MediaFile | None: ...


class MediaSigner(Protocol):
    """Turning a stored object into a link that expires."""

    def playback_url(self, media: MediaFile) -> str: ...


class AccessGuard(Protocol):
    """The one question about payment this service is allowed to ask."""

    async def require_access(self, *, user: User | None, course_id: UUID) -> None: ...


class AssignmentService:
    """The assignment page and the act of sending work in."""

    def __init__(
        self,
        *,
        unit_repo: UnitReader,
        course_repo: CourseReader,
        assignment_repo: AssignmentStore,
        enrollment_repo: EnrolmentStore,
        media_repo: MediaStore,
        media_service: MediaSigner,
        billing: AccessGuard,
    ) -> None:
        self.unit_repo = unit_repo
        self.course_repo = course_repo
        self.assignment_repo = assignment_repo
        self.enrollment_repo = enrollment_repo
        self.media_repo = media_repo
        self.media_service = media_service
        self.billing = billing

    async def get_page(self, *, unit_id: UUID, viewer: User) -> AssignmentOut:
        """The assignment with every attempt this student has made at it."""
        unit, course, assignment = await self._resolve(unit_id=unit_id, viewer=viewer)
        enrollment = await self._enrollment(user=viewer, course=course)
        submissions = await self.assignment_repo.list_submissions(
            enrollment_id=enrollment.id, assignment_id=assignment.id
        )
        rendered = await self._render(submissions)
        return AssignmentOut(
            unit_id=unit.id,
            title=unit.title,
            description=assignment.description or unit.summary,
            deadline_at=assignment.deadline_at,
            max_score=assignment.max_score,
            course_slug=course.slug,
            course_title=course.title,
            can_submit=_can_submit(submissions),
            submissions=rendered,
        )

    async def submit(self, *, unit_id: UUID, viewer: User, payload: SubmissionIn) -> AssignmentOut:
        """
        Send work in as the next attempt.

        Refused while an attempt is waiting for a reviewer: a second one would not be looked
        at any sooner and would push somebody else down the queue. Being late is recorded
        and accepted — the cost of it is a decision for the person marking the work.
        """
        _, course, assignment = await self._resolve(unit_id=unit_id, viewer=viewer)
        enrollment = await self._enrollment(user=viewer, course=course)
        submissions = await self.assignment_repo.list_submissions(
            enrollment_id=enrollment.id, assignment_id=assignment.id
        )
        if not _can_submit(submissions):
            raise SubmissionNotAllowedError(unit_id)

        now = datetime.now(UTC)
        is_late = assignment.deadline_at is not None and now > assignment.deadline_at
        if is_late and not assignment.allow_late:
            raise DeadlinePassedError(unit_id)

        await self._check_attachments(payload.media_ids, owner=viewer)
        attempt_no = await self.assignment_repo.next_attempt_no(
            enrollment_id=enrollment.id, assignment_id=assignment.id
        )
        await self.assignment_repo.add_submission(
            Submission(
                enrollment_id=enrollment.id,
                assignment_id=assignment.id,
                attempt_no=attempt_no,
                status=SubmissionStatus.SUBMITTED,
                comment=payload.comment,
                submitted_at=now,
                is_late=is_late,
            ),
            payload.media_ids,
        )
        return await self.get_page(unit_id=unit_id, viewer=viewer)

    async def _resolve(
        self, *, unit_id: UUID, viewer: User
    ) -> tuple[CourseUnit, Course, Assignment]:
        """The outline line, its course and the assignment behind it, or a refusal."""
        unit = await self.unit_repo.get_unit(unit_id)
        if unit is None or unit.kind is not CourseUnitKind.ASSIGNMENT:
            raise AssignmentNotFoundError(unit_id)
        course = await self.course_repo.get_published_by_id(unit.course_id)
        if course is None:
            raise AssignmentNotFoundError(unit_id)
        await self.billing.require_access(user=viewer, course_id=course.id)

        assignment = await self.assignment_repo.get_by_unit(unit.id)
        if assignment is None:
            # Created on first use, like a test: a line that already says «assignment» does
            # not need somebody to press a button to become one.
            assignment = await self.assignment_repo.create(
                Assignment(unit_id=unit.id, description=unit.summary)
            )
        return unit, course, assignment

    async def _enrollment(self, *, user: User, course: Course) -> Enrollment:
        """The study record, created on the way in if this is the student's first step."""
        await self.enrollment_repo.ensure(user_id=user.id, course_id=course.id, last_lesson_id=None)
        enrollment = await self.enrollment_repo.get(user_id=user.id, course_id=course.id)
        if enrollment is None:
            raise AssignmentNotFoundError(course.id)
        return enrollment

    async def _check_attachments(self, media_ids: Sequence[UUID], *, owner: User) -> None:
        """
        Every attachment must be a finished upload made by this very student.

        Without the ownership check an identifier from somebody else's work attaches their
        file to mine — and the reviewer sees it as mine.
        """
        for media_id in media_ids:
            media = await self.media_repo.get(media_id)
            if media is None or media.status is not MediaStatus.READY:
                raise AttachmentRejectedError(media_id)
            if media.uploaded_by_id != owner.id:
                raise AttachmentRejectedError(media_id)

    async def _render(self, submissions: Sequence[Submission]) -> list[SubmissionOut]:
        """Attempts with their files and reviews, in the order they were made."""
        ids = [submission.id for submission in submissions]
        files = await self.assignment_repo.list_files(ids)
        reviews = await self.assignment_repo.list_reviews(ids)
        by_submission: dict[UUID, list[AttachmentOut]] = {}
        for submission_id, media in files:
            by_submission.setdefault(submission_id, []).append(
                AttachmentOut(
                    id=media.id,
                    name=media.original_name,
                    size_bytes=media.size_bytes,
                    url=self.media_service.playback_url(media),
                )
            )
        latest_review: dict[UUID, tuple[SubmissionReview, str]] = {
            review.submission_id: (review, reviewer_name) for review, reviewer_name in reviews
        }
        return [
            SubmissionOut(
                id=submission.id,
                attempt_no=submission.attempt_no,
                status=submission.status,
                comment=submission.comment,
                submitted_at=submission.submitted_at,
                is_late=submission.is_late,
                attachments=by_submission.get(submission.id, []),
                review=_review_out(latest_review.get(submission.id)),
            )
            for submission in submissions
        ]


def _can_submit(submissions: Sequence[Submission]) -> bool:
    """
    Whether a new attempt may be started.

    No while one is waiting for a reviewer, no once the work has been accepted, yes
    otherwise — including after it was sent back for revision, which is exactly what
    «revision» means.
    """
    if not submissions:
        return True
    latest = submissions[-1]
    return latest.status not in (*PENDING_STATES, SubmissionStatus.ACCEPTED)


def _review_out(found: tuple[SubmissionReview, str] | None) -> ReviewOut | None:
    """A review as the student reads it, or nothing while nobody has looked at the work."""
    if found is None:
        return None
    review, reviewer_name = found
    return ReviewOut(
        score=review.score,
        comment=review.comment,
        decision=review.decision,
        reviewed_at=review.reviewed_at,
        reviewer_name=reviewer_name,
    )
