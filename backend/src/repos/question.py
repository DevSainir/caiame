from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.course_question import CourseQuestion


class QuestionRepo:
    """Data access for the questions shown under a course."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_course(self, course_id: UUID) -> Sequence[CourseQuestion]:
        """Every question of one course, in the order they are shown."""
        rows = await self.session.scalars(
            select(CourseQuestion)
            .where(CourseQuestion.course_id == course_id)
            .order_by(CourseQuestion.position)
        )
        return rows.all()

    async def get(self, question_id: UUID) -> CourseQuestion | None:
        """One question by its id."""
        question: CourseQuestion | None = await self.session.get(CourseQuestion, question_id)
        return question

    async def add(self, question: CourseQuestion) -> CourseQuestion:
        """Insert a question and hand it back with its id."""
        self.session.add(question)
        await self.session.flush()
        return question

    async def delete(self, question: CourseQuestion) -> None:
        """
        Remove a question.

        Physical deletion, unlike a lecture: nothing points at editorial text, and keeping
        a hidden copy of an answer nobody may see is a way to leak it later.
        """
        await self.session.delete(question)

    async def next_position(self, course_id: UUID) -> int:
        """The position a new question takes: after the last one."""
        last = await self.session.scalar(
            select(func.max(CourseQuestion.position)).where(CourseQuestion.course_id == course_id)
        )
        return int(last or 0) + 1

    async def flush(self) -> None:
        """Push pending changes so a failure surfaces inside the request."""
        await self.session.flush()
