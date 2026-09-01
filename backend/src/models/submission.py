from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin
from models.enums import SubmissionStatus


class Submission(UUIDMixin, TimeStampMixin, Base):
    """
    One attempt at an assignment by one student.

    Sending work back for revision creates the next submission instead of rewriting this
    one: the student has to be able to see what they were told last time, and the reviewer
    has to be able to see what changed. Rewriting destroys both after the first round.

    Tied to the study record rather than to the account, because that is what says this
    person is taking this course — and it survives access ending, exactly like the rest of
    their history.
    """

    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "assignment_id", "attempt_no", name="uq_submission_try"),
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        SAEnum(SubmissionStatus, name="submission_status", native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # A flag, not a refusal: whether the work was late is a fact, and what it costs is a
    # decision made by the person marking it.
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SubmissionFile(UUIDMixin, TimeStampMixin, Base):
    """One file attached to a submission. The file itself lives in private storage."""

    __tablename__ = "submission_files"

    submission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_file_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
