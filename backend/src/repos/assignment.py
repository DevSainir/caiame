from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.assignment import Assignment
from models.course_unit import CourseUnit
from models.enrollment import Enrollment
from models.enums import SubmissionStatus
from models.media_file import MediaFile
from models.submission import Submission, SubmissionFile
from models.submission_review import SubmissionReview
from models.user import User


class AssignmentRepo:
    """Data access for assignments, the work sent in for them and the reviews of it."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_unit(self, unit_id: UUID) -> Assignment | None:
        """The assignment attached to one line of the outline."""
        assignment: Assignment | None = await self.session.scalar(
            select(Assignment).where(Assignment.unit_id == unit_id)
        )
        return assignment

    async def create(self, assignment: Assignment) -> Assignment:
        """Attach an assignment to a line of the outline."""
        self.session.add(assignment)
        await self.session.flush()
        return assignment

    async def get_submission(self, submission_id: UUID) -> Submission | None:
        """One submission by its id, whoever it belongs to."""
        submission: Submission | None = await self.session.get(Submission, submission_id)
        return submission

    async def list_submissions(
        self, *, enrollment_id: UUID, assignment_id: UUID
    ) -> Sequence[Submission]:
        """Every attempt one student made at one assignment, oldest first."""
        rows = await self.session.scalars(
            select(Submission)
            .where(
                Submission.enrollment_id == enrollment_id,
                Submission.assignment_id == assignment_id,
            )
            .order_by(Submission.attempt_no)
        )
        return rows.all()

    async def next_attempt_no(self, *, enrollment_id: UUID, assignment_id: UUID) -> int:
        """
        The number the next attempt takes.

        Numbers, not overwrites: sending work back for revision has to leave the previous
        round readable to both sides.
        """
        last = await self.session.scalar(
            select(func.max(Submission.attempt_no)).where(
                Submission.enrollment_id == enrollment_id,
                Submission.assignment_id == assignment_id,
            )
        )
        return int(last or 0) + 1

    async def add_submission(self, submission: Submission, media_ids: Sequence[UUID]) -> Submission:
        """Store a submission together with the files attached to it."""
        self.session.add(submission)
        await self.session.flush()
        for position, media_id in enumerate(media_ids, start=1):
            self.session.add(
                SubmissionFile(
                    submission_id=submission.id, media_file_id=media_id, position=position
                )
            )
        await self.session.flush()
        return submission

    async def list_files(self, submission_ids: Sequence[UUID]) -> Sequence[tuple[UUID, MediaFile]]:
        """The files of the given submissions, with the media row behind each."""
        if not submission_ids:
            return []
        rows = await self.session.execute(
            select(SubmissionFile.submission_id, MediaFile)
            .join(MediaFile, MediaFile.id == SubmissionFile.media_file_id)
            .where(SubmissionFile.submission_id.in_(submission_ids))
            .order_by(SubmissionFile.position)
        )
        return [(submission_id, media) for submission_id, media in rows.all()]

    async def list_reviews(
        self, submission_ids: Sequence[UUID]
    ) -> Sequence[tuple[SubmissionReview, str]]:
        """
        Reviews of the given submissions with the name of whoever wrote each.

        The name travels with the review because the student sees it: work marked by
        «somebody» is work nobody can be asked about.
        """
        if not submission_ids:
            return []
        rows = await self.session.execute(
            select(SubmissionReview, User.full_name)
            .outerjoin(User, User.id == SubmissionReview.reviewer_id)
            .where(SubmissionReview.submission_id.in_(submission_ids))
            .order_by(SubmissionReview.reviewed_at)
        )
        return [(review, name or "") for review, name in rows.all()]

    async def add_review(self, review: SubmissionReview) -> SubmissionReview:
        """Store a review."""
        self.session.add(review)
        await self.session.flush()
        return review

    async def list_for_review(
        self, *, course_id: UUID | None, limit: int, offset: int
    ) -> Sequence[tuple[Submission, User, CourseUnit]]:
        """
        Work waiting to be looked at, oldest first.

        Oldest first on purpose: a queue sorted the other way leaves the first person who
        submitted waiting the longest.
        """
        statement = (
            select(Submission, User, CourseUnit)
            .join(Enrollment, Enrollment.id == Submission.enrollment_id)
            .join(User, User.id == Enrollment.user_id)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .join(CourseUnit, CourseUnit.id == Assignment.unit_id)
            .where(Submission.status.in_([SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW]))
            .order_by(Submission.submitted_at)
            .limit(limit)
            .offset(offset)
        )
        if course_id is not None:
            statement = statement.where(CourseUnit.course_id == course_id)
        rows = await self.session.execute(statement)
        return [(submission, student, unit) for submission, student, unit in rows.all()]

    async def count_for_review(self, *, course_id: UUID | None) -> int:
        """How long the queue is in total."""
        statement = (
            select(func.count(Submission.id))
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .join(CourseUnit, CourseUnit.id == Assignment.unit_id)
            .where(Submission.status.in_([SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW]))
        )
        if course_id is not None:
            statement = statement.where(CourseUnit.course_id == course_id)
        return int(await self.session.scalar(statement) or 0)

    async def get_assignment(self, assignment_id: UUID) -> Assignment | None:
        """One assignment by its id."""
        assignment: Assignment | None = await self.session.get(Assignment, assignment_id)
        return assignment

    async def get_unit_of(self, assignment: Assignment) -> CourseUnit | None:
        """The line of the outline an assignment belongs to."""
        unit: CourseUnit | None = await self.session.get(CourseUnit, assignment.unit_id)
        return unit

    async def owner_of(self, submission: Submission) -> tuple[Enrollment, User] | None:
        """The study record and the person behind one submission."""
        row = await self.session.execute(
            select(Enrollment, User)
            .join(User, User.id == Enrollment.user_id)
            .where(Enrollment.id == submission.enrollment_id)
        )
        found = row.first()
        return (found[0], found[1]) if found else None

    async def set_status(
        self, submission: Submission, *, status: SubmissionStatus, at: datetime | None = None
    ) -> Submission:
        """Move a submission to the next state."""
        submission.status = status
        if at is not None:
            submission.submitted_at = at
        await self.session.flush()
        return submission
