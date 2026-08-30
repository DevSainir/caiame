from uuid import UUID

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin


class Quiz(UUIDMixin, TimeStampMixin, Base):
    """
    The settings of one test: what counts as a pass and how many tries there are.

    A table of its own rather than columns on the unit: only units of one kind have these,
    and nullable columns that mean nothing for the other kinds are how a table stops
    describing anything.
    """

    __tablename__ = "quizzes"

    unit_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_units.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # In points, not percent: questions carry different weights.
    passing_score: Mapped[int] = mapped_column(Integer, nullable=False)
    # NULL means «as many as you like». A number here is enforced by the unique index on
    # the attempt, not by a check-then-insert, which two parallel requests both pass.
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
