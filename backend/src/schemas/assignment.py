from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from models.enums import ReviewDecision, SubmissionStatus


class AttachmentOut(BaseModel):
    """One file of a submission, with a link that expires."""

    id: UUID
    name: str
    size_bytes: int
    url: str


class ReviewOut(BaseModel):
    """
    What the reviewer wrote about one attempt.

    The comment goes to the student in full — there is nothing here that is «for us»,
    and there is no field where such a thing could hide.
    """

    score: int
    comment: str
    decision: ReviewDecision
    reviewed_at: datetime
    reviewer_name: str


class SubmissionOut(BaseModel):
    """One attempt at an assignment, as its author sees it."""

    id: UUID
    attempt_no: int
    status: SubmissionStatus
    comment: str
    submitted_at: datetime | None
    is_late: bool
    attachments: list[AttachmentOut]
    review: ReviewOut | None


class AssignmentOut(BaseModel):
    """The assignment page: what to do, by when, and everything sent in so far."""

    unit_id: UUID
    title: str
    description: str
    deadline_at: datetime | None
    max_score: int
    course_slug: str
    course_title: str
    # Whether the student may send work in right now. False while an attempt is waiting for
    # a reviewer and after the work has been accepted.
    can_submit: bool
    submissions: list[SubmissionOut]


class SubmissionIn(BaseModel):
    """Work being sent in: a note and the files that were uploaded for it."""

    comment: str = Field(default="", max_length=5000)
    media_ids: list[UUID] = Field(default_factory=list, max_length=10)


class ReviewIn(BaseModel):
    """A reviewer's verdict on one attempt."""

    score: int = Field(ge=0, le=1000)
    comment: str = Field(default="", max_length=5000)
    decision: ReviewDecision


class QueueRowOut(BaseModel):
    """One piece of work waiting to be looked at."""

    id: UUID
    student_name: str
    student_email: str
    course_title: str
    assignment_title: str
    attempt_no: int
    submitted_at: datetime | None
    is_late: bool
    status: SubmissionStatus


class QueuePageOut(BaseModel):
    """A page of the review queue."""

    items: list[QueueRowOut]
    total: int


class SubmissionDetailOut(BaseModel):
    """One submission as the reviewer sees it, with everything sent before it."""

    id: UUID
    student_name: str
    student_email: str
    assignment_title: str
    max_score: int
    attempt_no: int
    status: SubmissionStatus
    comment: str
    submitted_at: datetime | None
    is_late: bool
    attachments: list[AttachmentOut]
    history: list[SubmissionOut]
