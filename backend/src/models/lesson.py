from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin
from models.enums import LessonKind


class Lesson(UUIDMixin, TimeStampMixin, Base):
    """
    One lecture inside a module — the smallest thing a student can finish.

    Never deleted physically: progress rows point at it, and a cascade would erase somebody's
    history. A removed lesson leaves the denominator of the percentage and stays in the past.
    """

    __tablename__ = "lessons"
    # Deferred on purpose: swapping two rows passes through a state where both hold
    # the same position for an instant. Checked at commit, the constraint sees the
    # finished order; checked per statement, it would refuse every reorder.
    __table_args__ = (
        UniqueConstraint(
            "unit_id",
            "position",
            name="uq_lesson_position",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    unit_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    kind: Mapped[LessonKind] = mapped_column(
        SAEnum(LessonKind, name="lesson_kind", native_enum=False, length=20), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Where the material lives. A signed link from private storage replaces this the day
    # media-video lands; until then it is a public path.
    asset_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # An optional lesson stays out of the denominator, which is the safe way to add
    # material to a course people are already taking.
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
