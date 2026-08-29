from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin
from models.enums import UnitStatus


class UnitProgress(UUIDMixin, TimeStampMixin, Base):
    """
    One fact: how far one student got in one unit.

    The percentage of the course is never stored — it is counted from these rows. A stored
    number goes out of step with reality silently, and nobody notices until a student is
    told they finished a course they did not.
    """

    __tablename__ = "unit_progress"
    __table_args__ = (UniqueConstraint("user_id", "unit_id", name="uq_progress_user_unit"),)

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[UnitStatus] = mapped_column(
        SAEnum(UnitStatus, name="unit_status", native_enum=False, length=20), nullable=False
    )
