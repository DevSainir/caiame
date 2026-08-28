from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.accreditation import Accreditation
from models.specialization import Specialization


class SpecializationRepo:
    """Data access for specializations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self) -> Sequence[Specialization]:
        """Return every specialization offered in the filters, in display order."""
        rows = await self.session.scalars(
            select(Specialization)
            .where(Specialization.is_active.is_(True))
            .order_by(Specialization.position, Specialization.name)
        )
        return rows.all()


class AccreditationRepo:
    """Data access for accreditation schemes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self) -> Sequence[Accreditation]:
        """Return every accreditation scheme offered in the filters, in display order."""
        rows = await self.session.scalars(
            select(Accreditation)
            .where(Accreditation.is_active.is_(True))
            .order_by(Accreditation.position, Accreditation.name)
        )
        return rows.all()
