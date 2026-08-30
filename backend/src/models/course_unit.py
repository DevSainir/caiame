from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin
from models.enums import CourseUnitKind


class CourseUnit(UUIDMixin, TimeStampMixin, Base):
    """One line of the course outline: a module, an assignment or a test."""

    __tablename__ = "course_units"
    # Deferred for the same reason as the lessons: a swap passes through a state where
    # two rows stand on one position.
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "kind",
            "position",
            name="uq_unit_position",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[CourseUnitKind] = mapped_column(
        SAEnum(CourseUnitKind, name="course_unit_kind", native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    # Order inside its own kind, so modules and works are numbered independently.
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(String(300), nullable=False, default="")
