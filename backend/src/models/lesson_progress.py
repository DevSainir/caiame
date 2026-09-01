from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin
from models.enums import UnitStatus


class LessonProgress(UUIDMixin, TimeStampMixin, Base):
    """
    One fact: how far one student got in one lesson.

    `completed_at` is written once and never moved: the mark is an upsert, and a student
    who reopens a finished lesson has not finished it a second time.
    """

    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress"),)

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[UnitStatus] = mapped_column(
        SAEnum(UnitStatus, name="unit_status", native_enum=False, length=20), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Where the student is now. Moves in both directions, including backwards, and exists
    # for one thing: reopening a lecture where it was left.
    last_position_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # How much was actually played. Only ever grows, and only by time that really passed —
    # this is the number that decides whether a lecture counts as watched. Keeping the two
    # apart is the whole point: with one field, dragging the slider to the end finishes the
    # lecture without watching a second of it.
    watched_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
