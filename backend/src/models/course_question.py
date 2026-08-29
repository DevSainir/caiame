from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin


class CourseQuestion(UUIDMixin, TimeStampMixin, Base):
    """
    A question about a course with its answer, shown in the discussion block.

    Editorial content rather than a conversation: a real discussion — students asking,
    instructors replying — is its own feature with its own moderation. This is the part of
    it that already has answers.
    """

    __tablename__ = "course_questions"

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question: Mapped[str] = mapped_column(String(300), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
