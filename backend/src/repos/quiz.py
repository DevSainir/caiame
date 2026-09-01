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

    async def answered_question_ids(self, question_ids: Sequence[UUID]) -> set[UUID]:
        """
        Which of these questions somebody has already answered.

        This is what decides whether a question may still be edited: once an answer points
        at it, changing the wording turns a stored «wrong» into a verdict nobody can
        explain afterwards.
        """
        if not question_ids:
            return set()
        rows = await self.session.scalars(
            select(QuizAttemptAnswer.question_id).where(
                QuizAttemptAnswer.question_id.in_(question_ids)
            )
        )
        return set(rows.all())

    async def add_question(self, question: QuizQuestion, options: Sequence[QuizOption]) -> None:
        """Insert a question together with its options."""
        self.session.add(question)
        await self.session.flush()
        for option in options:
            option.question_id = question.id
            self.session.add(option)
        await self.session.flush()

    async def replace_options(self, question: QuizQuestion, options: Sequence[QuizOption]) -> None:
        """Swap the options of a question that nobody has answered yet."""
        existing = await self.session.scalars(
            select(QuizOption).where(QuizOption.question_id == question.id)
        )
        for option in existing.all():
            await self.session.delete(option)
        await self.session.flush()
        for option in options:
            option.question_id = question.id
            self.session.add(option)
        await self.session.flush()

    async def next_question_position(self, quiz_id: UUID) -> int:
        """The position a new question takes: after the last live one."""
        last = await self.session.scalar(
            select(func.max(QuizQuestion.position)).where(
                QuizQuestion.quiz_id == quiz_id, QuizQuestion.deleted_at.is_(None)
            )
        )
        return int(last or 0) + 1

    async def get_question(self, question_id: UUID) -> QuizQuestion | None:
        """One live question by its id."""
        question: QuizQuestion | None = await self.session.scalar(
            select(QuizQuestion).where(
                QuizQuestion.id == question_id, QuizQuestion.deleted_at.is_(None)
            )
        )
        return question

    async def create_quiz(self, quiz: Quiz) -> Quiz:
        """Attach a test to a line of the outline."""
        self.session.add(quiz)
        await self.session.flush()
        return quiz

    async def flush(self) -> None:
        """Push pending changes so a constraint failure surfaces inside the request."""
        await self.session.flush()

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
