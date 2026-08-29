from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin


class CourseBenefit(UUIDMixin, TimeStampMixin, Base):
    """
    One reason to take the course, as the academy words it on its own posters.

    A table rather than a field on the course: every course carries several of these, they
    are edited as content, and half of them are the same sentence for the whole catalogue.
    """

    __tablename__ = "course_benefits"

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
