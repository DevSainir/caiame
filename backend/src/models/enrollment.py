from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin


class Enrollment(UUIDMixin, TimeStampMixin, Base):
    """
    A study record: this student is taking this course.

    Not the right to open it — that is `entitlement`, and the two drift apart on purpose.
    Access ends and the record stays, with all of the progress under it, so that a student
    who pays again continues from where they stopped rather than from the beginning.

    Created the first time a student opens material they have the right to, and never
    deleted: deleting it would delete somebody's history of studying.
    """

    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollment_student"),)

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Fixed at the moment the condition was met and never recalculated: the percentage is
    # derived and can fall, but finishing a course is an event and does not un-happen.
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_lesson_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )
