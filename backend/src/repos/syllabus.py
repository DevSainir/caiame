from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, UnitStatus
from models.unit_progress import UnitProgress

# Display order is spelled out instead of falling out of the enum: sorting by the stored
# value gives alphabetical order, and renaming a member would silently reshuffle the page.
#
# Written as comparisons and not as the shorter `case({...}, value=...)`: the dictionary
# form compares the column against the enum members without putting them through the
# column's type, the stored names never match, every row gets NULL — and the list quietly
# falls back to sorting by position alone, interleaving assignments with tests.
KIND_ORDER = case(
    (CourseUnit.kind == CourseUnitKind.MODULE, 0),
    (CourseUnit.kind == CourseUnitKind.ASSIGNMENT, 1),
    else_=2,
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

    async def get_unit(self, unit_id: UUID) -> CourseUnit | None:
        """One line of the outline by its id."""
        unit: CourseUnit | None = await self.session.scalar(
            select(CourseUnit).where(CourseUnit.id == unit_id)
        )
        return unit

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

    async def mark_unit(self, *, user_id: UUID, unit_id: UUID, status: UnitStatus) -> None:
        """
        Record how far a student got in one unit of the outline.

        An upsert that never walks a status backwards: a second, worse attempt at a test
        does not take away a pass that already happened.
        """
        statement = insert(UnitProgress).values(user_id=user_id, unit_id=unit_id, status=status)
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[UnitProgress.user_id, UnitProgress.unit_id],
                set_={"status": status},
                where=UnitProgress.status != UnitStatus.DONE,
            )
        )
