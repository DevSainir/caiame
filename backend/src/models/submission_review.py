from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin
from models.enums import ReviewDecision


class SubmissionReview(UUIDMixin, TimeStampMixin, Base):
    """
    What a reviewer decided about one submission.

    Named apart from `Review`, which is a student's opinion of a course — two different
    things that would otherwise share a word and, sooner or later, a query.

    The comment is shown to the student in full. Notes «for ourselves» do not belong in
    this table: if they are ever needed, that is a separate column with an explicit name
    and a separate response schema, so nobody leaks them by adding a field.
    """

    __tablename__ = "submission_reviews"

    submission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decision: Mapped[ReviewDecision] = mapped_column(
        SAEnum(ReviewDecision, name="review_decision", native_enum=False, length=20), nullable=False
    )
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
