from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.course_benefit import CourseBenefit


class BenefitRepo:
    """Data access for the «why this course» blocks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_course(self, course_id: UUID) -> Sequence[CourseBenefit]:
        """Every reason listed under one course, in the order they are shown."""
        rows = await self.session.scalars(
            select(CourseBenefit)
            .where(CourseBenefit.course_id == course_id)
            .order_by(CourseBenefit.position)
        )
        return rows.all()
