from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin


class Assignment(UUIDMixin, TimeStampMixin, Base):
    """
    A piece of work a person checks by hand, attached to one line of the course outline.

    Hangs off the outline line rather than off a lesson: in this product an assignment is a
    line of the programme in its own right, exactly like a test, and it is the line that
    students see on the course page.
    """

    __tablename__ = "assignments"

    unit_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_units.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    # Off by default, and deliberately. An automatic refusal a minute after the deadline
    # buys no review time and produces a queue of appeals; lateness is a flag on the work
    # and a decision for the person marking it.
    allow_late: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
