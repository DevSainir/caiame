from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.course import Course
from models.entitlement import Entitlement
from models.enums import AccessSource
from models.user import User


class EntitlementRepo:
    """Data access for the right to open a course. Only the billing service comes here."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def has_live(self, *, user_id: UUID, course_id: UUID, at: datetime) -> bool:
        """
        Whether this account holds a right to this course right now.

        «Now» is decided at the question, not by a nightly job that switches expired rights
        off: such a job is always late by its own interval, which is a day of free access
        and, worse, a difference between what the page shows and what the backend allows.
        A right to the whole catalogue (`course_id` empty) answers here too.
        """
        row = await self.session.scalar(
            select(Entitlement.id)
            .where(
                Entitlement.user_id == user_id,
                or_(Entitlement.course_id == course_id, Entitlement.course_id.is_(None)),
                Entitlement.revoked_at.is_(None),
                Entitlement.starts_at <= at,
                or_(Entitlement.ends_at.is_(None), Entitlement.ends_at > at),
            )
            .limit(1)
        )
        return row is not None

    async def find_live(
        self, *, user_id: UUID, course_id: UUID | None, at: datetime
    ) -> Entitlement | None:
        """
        The live right this account already holds to exactly this course, if any.

        Exactly this one: a right to the whole catalogue and a right to one course are two
        different rights, and withdrawing one must not look like withdrawing the other.
        """
        entitlement: Entitlement | None = await self.session.scalar(
            select(Entitlement)
            .where(
                Entitlement.user_id == user_id,
                Entitlement.course_id.is_(None)
                if course_id is None
                else Entitlement.course_id == course_id,
                Entitlement.revoked_at.is_(None),
                Entitlement.starts_at <= at,
                or_(Entitlement.ends_at.is_(None), Entitlement.ends_at > at),
            )
            .limit(1)
        )
        return entitlement

    async def live_for_user(self, *, user_id: UUID, at: datetime) -> Sequence[UUID | None]:
        """Every course this account may open now; an empty id means the whole catalogue."""
        rows = await self.session.scalars(
            select(Entitlement.course_id).where(
                Entitlement.user_id == user_id,
                Entitlement.revoked_at.is_(None),
                Entitlement.starts_at <= at,
                or_(Entitlement.ends_at.is_(None), Entitlement.ends_at > at),
            )
        )
        return rows.all()

    async def get(self, entitlement_id: UUID) -> Entitlement | None:
        """One grant by its id."""
        entitlement: Entitlement | None = await self.session.get(Entitlement, entitlement_id)
        return entitlement

    async def create(
        self,
        *,
        user_id: UUID,
        course_id: UUID | None,
        source: AccessSource,
        granted_by_id: UUID | None,
        reason: str,
        ends_at: datetime | None,
    ) -> Entitlement:
        """Grant a right, stamped with who granted it and why."""
        entitlement = Entitlement(
            user_id=user_id,
            course_id=course_id,
            source=source,
            starts_at=datetime.now(UTC),
            ends_at=ends_at,
            granted_by_id=granted_by_id,
            reason=reason,
        )
        self.session.add(entitlement)
        await self.session.flush()
        return entitlement

    async def revoke(self, entitlement: Entitlement, *, at: datetime) -> Entitlement:
        """Withdraw a right without erasing the fact that it existed."""
        entitlement.revoked_at = at
        await self.session.flush()
        return entitlement

    async def list_grants(
        self, *, course_id: UUID | None, limit: int, offset: int
    ) -> list[tuple[Entitlement, User, Course | None]]:
        """
        Grants with the student and the course behind them, newest first.

        The course is joined outwards because a grant may name the whole catalogue instead
        of one course; such a row arrives with nothing in that column.
        """
        statement = (
            select(Entitlement, User, Course)
            .join(User, User.id == Entitlement.user_id)
            .outerjoin(Course, Course.id == Entitlement.course_id)
            .order_by(Entitlement.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if course_id is not None:
            statement = statement.where(Entitlement.course_id == course_id)
        rows = await self.session.execute(statement)
        return [(entitlement, student, course) for entitlement, student, course in rows.all()]

    async def count_grants(self, *, course_id: UUID | None) -> int:
        """How many grants the list would hold in total, for the «show more» decision."""
        statement = select(Entitlement.id)
        if course_id is not None:
            statement = statement.where(Entitlement.course_id == course_id)
        rows = await self.session.scalars(statement)
        return len(rows.all())
