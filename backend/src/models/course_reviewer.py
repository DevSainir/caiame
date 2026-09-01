from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin


class CourseReviewer(UUIDMixin, TimeStampMixin, Base):
    """
    Who checks the work sent in for one course.

    A table rather than a role, because the question is «which courses», not «is this
    person staff». An administrator sees every queue by their rung; a teacher sees the
    courses they were put on and nothing else — somebody else's students' work is not
    theirs to read.
    """

    __tablename__ = "course_reviewers"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_course_reviewer"),)

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
