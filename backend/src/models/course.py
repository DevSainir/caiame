from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimeStampMixin, UUIDMixin
from models.enums import CourseStatus

if TYPE_CHECKING:
    from models.accreditation import Accreditation
    from models.specialization import Specialization


class Course(UUIDMixin, TimeStampMixin, Base):
    """A course in the catalogue: what a student browses, buys and then studies."""

    __tablename__ = "courses"

    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[CourseStatus] = mapped_column(
        SAEnum(CourseStatus, name="course_status", native_enum=False, length=20),
        default=CourseStatus.DRAFT,
        nullable=False,
        index=True,
    )
    specialization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("specializations.id"), nullable=False, index=True
    )
    accreditation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accreditations.id"), nullable=True, index=True
    )

    # Money is an integer in minor units plus a currency code, never a float.
    price_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="KGS", nullable=False)

    credit_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    specialization: Mapped["Specialization"] = relationship(lazy="raise")
    accreditation: Mapped["Accreditation | None"] = relationship(lazy="raise")
