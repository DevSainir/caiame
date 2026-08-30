from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin


class QuizAttempt(UUIDMixin, TimeStampMixin, Base):
    """
    One run at a test by one student.

    `number` is unique per student and quiz, so the attempt limit is decided by the database
    and not by a check followed by an insert — two parallel requests pass such a check both.
    """

    __tablename__ = "quiz_attempts"
    __table_args__ = (UniqueConstraint("user_id", "quiz_id", "number", name="uq_attempt_number"),)

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quiz_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)


class QuizAttemptAnswer(UUIDMixin, TimeStampMixin, Base):
    """What the student picked in one question, and what the server made of it."""

    __tablename__ = "quiz_attempt_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_attempt_answer"),)

    attempt_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quiz_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Option ids as sent, so a later look at the attempt shows what was picked and not only
    # the verdict. JSON because one question may take several of them.
    selected_option_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False)
