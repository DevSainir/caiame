from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.quiz import Quiz
from models.quiz_attempt import QuizAttempt, QuizAttemptAnswer
from models.quiz_question import QuizOption, QuizQuestion


class QuizRepo:
    """Data access for tests, their questions and the attempts at them."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_unit(self, unit_id: UUID) -> Quiz | None:
        """The test attached to one line of the course outline."""
        quiz: Quiz | None = await self.session.scalar(select(Quiz).where(Quiz.unit_id == unit_id))
        return quiz

    async def list_questions(self, quiz_id: UUID) -> Sequence[QuizQuestion]:
        """
        Live questions of one test, with their options loaded.

        A question removed after somebody answered it stays in the database and out of new
        attempts; old attempts keep pointing at it and stay explainable.
        """
        rows = await self.session.scalars(
            select(QuizQuestion)
            .where(QuizQuestion.quiz_id == quiz_id, QuizQuestion.deleted_at.is_(None))
            .order_by(QuizQuestion.position)
        )
        return rows.all()

    async def list_options(self, question_ids: Sequence[UUID]) -> Sequence[QuizOption]:
        """Options of the given questions, in display order."""
        if not question_ids:
            return []
        rows = await self.session.scalars(
            select(QuizOption)
            .where(QuizOption.question_id.in_(question_ids))
            .order_by(QuizOption.position)
        )
        return rows.all()

    async def latest_attempt(self, *, user_id: UUID, quiz_id: UUID) -> QuizAttempt | None:
        """The student's most recent attempt at this test, if there was one."""
        attempt: QuizAttempt | None = await self.session.scalar(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .order_by(QuizAttempt.number.desc())
            .limit(1)
        )
        return attempt

    async def count_attempts(self, *, user_id: UUID, quiz_id: UUID) -> int:
        """How many attempts this student has already spent."""
        return int(
            await self.session.scalar(
                select(func.count(QuizAttempt.id)).where(
                    QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id
                )
            )
            or 0
        )

    async def add_attempt(self, attempt: QuizAttempt, answers: Sequence[QuizAttemptAnswer]) -> None:
        """Store a graded attempt together with the answers it was graded from."""
        self.session.add(attempt)
        await self.session.flush()
        for answer in answers:
            answer.attempt_id = attempt.id
            self.session.add(answer)
