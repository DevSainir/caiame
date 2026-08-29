from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
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
