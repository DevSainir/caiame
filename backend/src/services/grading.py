"""
The reviewer's side: the queue of work waiting and the verdict on one piece of it.

Two refusals hold this together. Nobody reviews their own work — the check is on the study
record behind the submission, not on a name. And nothing is overwritten: a verdict is a new
row, and «needs revision» opens the next attempt rather than reopening this one.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from models.assignment import Assignment
from models.course_unit import CourseUnit
from models.enrollment import Enrollment
from models.enums import ReviewDecision, SubmissionStatus, UnitStatus
from models.media_file import MediaFile
from models.submission import Submission
from models.submission_review import SubmissionReview
from models.user import User
from schemas.assignment import (
    AttachmentOut,
    QueuePageOut,
    QueueRowOut,
    ReviewIn,
    ReviewOut,
    SubmissionDetailOut,
    SubmissionOut,
)


class SubmissionNotFoundError(Exception):
    """No such submission."""


class SelfReviewError(Exception):
    """A reviewer cannot mark their own work."""


class AlreadyDecidedError(Exception):
    """This attempt has already been marked; a further round is a new attempt."""


class GradingStore(Protocol):
    """What the review screen needs from storage."""

    async def get_submission(self, submission_id: UUID) -> Submission | None: ...
    async def list_for_review(
        self, *, course_id: UUID | None, limit: int, offset: int
    ) -> Sequence[tuple[Submission, User, CourseUnit]]: ...
    async def count_for_review(self, *, course_id: UUID | None) -> int: ...
    async def list_files(
        self, submission_ids: Sequence[UUID]
    ) -> Sequence[tuple[UUID, MediaFile]]: ...
    async def list_reviews(
        self, submission_ids: Sequence[UUID]
    ) -> Sequence[tuple[SubmissionReview, str]]: ...
    async def list_submissions(
        self, *, enrollment_id: UUID, assignment_id: UUID
    ) -> Sequence[Submission]: ...
    async def add_review(self, review: SubmissionReview) -> SubmissionReview: ...
    async def owner_of(self, submission: Submission) -> tuple[Enrollment, User] | None: ...
    async def set_status(
        self, submission: Submission, *, status: SubmissionStatus, at: datetime | None = None
    ) -> Submission: ...
    async def get_assignment(self, assignment_id: UUID) -> Assignment | None: ...
    async def get_unit_of(self, assignment: Assignment) -> CourseUnit | None: ...


class ProgressWriter(Protocol):
    """Where the course page reads whether a line of the outline is finished."""

    async def mark_unit(self, *, user_id: UUID, unit_id: UUID, status: UnitStatus) -> None: ...


class MediaSigner(Protocol):
    """Turning a stored object into a link that expires."""

    def playback_url(self, media: MediaFile) -> str: ...


class GradingService:
    """The queue of work to look at, and what happens when somebody looks at it."""

    def __init__(
        self,
        *,
        assignment_repo: GradingStore,
        progress_repo: ProgressWriter,
        media_service: MediaSigner,
    ) -> None:
        self.assignment_repo = assignment_repo
        self.progress_repo = progress_repo
        self.media_service = media_service

    async def queue(self, *, course_id: UUID | None, limit: int, offset: int) -> QueuePageOut:
        """Work waiting for a reviewer, the one who has waited longest first."""
        rows = await self.assignment_repo.list_for_review(
            course_id=course_id, limit=limit, offset=offset
        )
        total = await self.assignment_repo.count_for_review(course_id=course_id)
        return QueuePageOut(
            items=[
                QueueRowOut(
                    id=submission.id,
                    student_name=student.full_name,
                    student_email=student.email,
                    course_title="",
                    assignment_title=unit.title,
                    attempt_no=submission.attempt_no,
                    submitted_at=submission.submitted_at,
                    is_late=submission.is_late,
                    status=submission.status,
                )
                for submission, student, unit in rows
            ],
            total=total,
        )

    async def get_submission(self, submission_id: UUID) -> SubmissionDetailOut:
        """One piece of work with its files and everything the student sent before it."""
        submission = await self._submission(submission_id)
        owner = await self.assignment_repo.owner_of(submission)
        if owner is None:
            raise SubmissionNotFoundError(submission_id)
        enrollment, student = owner

        assignment = await self.assignment_repo.get_assignment(submission.assignment_id)
        unit = await self.assignment_repo.get_unit_of(assignment) if assignment else None
        history = await self.assignment_repo.list_submissions(
            enrollment_id=enrollment.id, assignment_id=submission.assignment_id
        )
        rendered = await self._render(history)
        current = next((item for item in rendered if item.id == submission.id), None)

        return SubmissionDetailOut(
            id=submission.id,
            student_name=student.full_name,
            student_email=student.email,
            assignment_title=unit.title if unit else "",
            max_score=assignment.max_score if assignment else 0,
            attempt_no=submission.attempt_no,
            status=submission.status,
            comment=submission.comment,
            submitted_at=submission.submitted_at,
            is_late=submission.is_late,
            attachments=current.attachments if current else [],
            history=[item for item in rendered if item.id != submission.id],
        )

    async def review(
        self, *, submission_id: UUID, reviewer: User, payload: ReviewIn
    ) -> SubmissionDetailOut:
        """
        Record a verdict.

        Accepting closes the line on the course page. Sending back for revision leaves it
        open — the status is not rolled back, because it never went up.
        """
        submission = await self._submission(submission_id)
        if submission.status in (SubmissionStatus.ACCEPTED, SubmissionStatus.NEEDS_REVISION):
            raise AlreadyDecidedError(submission_id)

        owner = await self.assignment_repo.owner_of(submission)
        if owner is None:
            raise SubmissionNotFoundError(submission_id)
        enrollment, _ = owner
        if enrollment.user_id == reviewer.id:
            raise SelfReviewError(submission_id)

        await self.assignment_repo.add_review(
            SubmissionReview(
                submission_id=submission.id,
                reviewer_id=reviewer.id,
                score=payload.score,
                comment=payload.comment,
                decision=payload.decision,
                reviewed_at=datetime.now(UTC),
            )
        )
        accepted = payload.decision is ReviewDecision.ACCEPTED
        await self.assignment_repo.set_status(
            submission,
            status=SubmissionStatus.ACCEPTED if accepted else SubmissionStatus.NEEDS_REVISION,
        )

        if accepted:
            assignment = await self.assignment_repo.get_assignment(submission.assignment_id)
            unit = await self.assignment_repo.get_unit_of(assignment) if assignment else None
            if unit is not None:
                await self.progress_repo.mark_unit(
                    user_id=enrollment.user_id, unit_id=unit.id, status=UnitStatus.DONE
                )
        return await self.get_submission(submission_id)

    async def _submission(self, submission_id: UUID) -> Submission:
        """One submission, or a refusal that says nothing about what exists."""
        submission = await self.assignment_repo.get_submission(submission_id)
        if submission is None:
            raise SubmissionNotFoundError(submission_id)
        return submission

    async def _render(self, submissions: Sequence[Submission]) -> list[SubmissionOut]:
        """Attempts with their files and reviews."""
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
        found: dict[UUID, tuple[SubmissionReview, str]] = {
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
                review=_review_out(found.get(submission.id)),
            )
            for submission in submissions
        ]


def _review_out(found: tuple[SubmissionReview, str] | None) -> ReviewOut | None:
    """A review as both sides read it."""
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
