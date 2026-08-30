from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin
from models.enums import QuestionKind


class QuizQuestion(UUIDMixin, TimeStampMixin, Base):
    """
    One question of a test.

    Never edited once somebody has answered it: a changed wording turns a stored «wrong»
    into a verdict nobody can explain. An edit creates a new question and marks this one
    deleted, which keeps old attempts explainable and leaves new ones alone.
    """

    __tablename__ = "quiz_questions"

    quiz_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[QuestionKind] = mapped_column(
        SAEnum(QuestionKind, name="question_kind", native_enum=False, length=20), nullable=False
    )
    points: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuizOption(UUIDMixin, TimeStampMixin, Base):
    """
    One option of a question. `is_correct` never leaves the backend.

    It stays out of the student's response by living in a schema that has no such field,
    not by filtering: a filter breaks the first time somebody adds a field and forgets it.
    """

    __tablename__ = "quiz_options"

    question_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quiz_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
