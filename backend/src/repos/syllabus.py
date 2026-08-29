from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.course_unit import CourseUnit
from models.enums import CourseUnitKind
from models.unit_progress import UnitProgress

# Display order is spelled out instead of falling out of the enum: sorting by the stored
# value gives alphabetical order, and renaming a member would silently reshuffle the page.
KIND_ORDER = case(
    {
        CourseUnitKind.MODULE: 0,
        CourseUnitKind.ASSIGNMENT: 1,
        CourseUnitKind.TEST: 2,
    },
    value=CourseUnit.kind,
)


class SyllabusRepo:
    """Data access for the course outline and for one student's facts about it."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_units(self, course_id: UUID) -> Sequence[CourseUnit]:
        """Every module and work of one course, in the order they are shown."""
        rows = await self.session.scalars(
            select(CourseUnit)
            .where(CourseUnit.course_id == course_id)
            .order_by(KIND_ORDER, CourseUnit.position)
        )
        return rows.all()

    async def statuses_for(self, *, user_id: UUID, course_id: UUID) -> dict[UUID, str]:
        """
        One student's status per unit, as a lookup keyed by unit.

        A dictionary rather than a join onto the units: the outline is public and the facts
        are not, so they are fetched separately and only for the account that asked.
        """
        rows = await self.session.execute(
            select(UnitProgress.unit_id, UnitProgress.status)
            .join(CourseUnit, CourseUnit.id == UnitProgress.unit_id)
            .where(UnitProgress.user_id == user_id, CourseUnit.course_id == course_id)
        )
        return {unit_id: str(status) for unit_id, status in rows.all()}
