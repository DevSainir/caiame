from collections.abc import Sequence

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.accreditation import Accreditation
from models.course import Course
from models.enums import CourseStatus, DifficultyLevel
from models.specialization import Specialization


class CourseRepo:
    """Data access for courses. Knows SQL, decides nothing."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_published(
        self,
        *,
        specialization_slug: str | None,
        accreditation_slug: str | None,
        difficulty: DifficultyLevel | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Course], int]:
        """Return one page of published courses and the total number that match the filters."""
        conditions = self._conditions(
            specialization_slug=specialization_slug,
            accreditation_slug=accreditation_slug,
            difficulty=difficulty,
            search=search,
        )

        total: int | None = await self.session.scalar(
            select(func.count(Course.id))
            .select_from(Course)
            .join(Specialization, Course.specialization_id == Specialization.id)
            .outerjoin(Accreditation, Course.accreditation_id == Accreditation.id)
            .where(*conditions)
        )

        rows = await self.session.scalars(
            self._base_query()
            .where(*conditions)
            .order_by(Course.created_at.desc(), Course.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return rows.all(), total or 0

    def _base_query(self) -> Select[tuple[Course]]:
        """
        Catalogue query with both taxonomies loaded up front.

        Relations are declared `lazy="raise"`, so a missing eager load fails here in a test
        instead of firing a lazy query inside the serializer, outside the session.
        """
        return (
            select(Course)
            .join(Specialization, Course.specialization_id == Specialization.id)
            .outerjoin(Accreditation, Course.accreditation_id == Accreditation.id)
            .options(selectinload(Course.specialization), selectinload(Course.accreditation))
        )

    def _conditions(
        self,
        *,
        specialization_slug: str | None,
        accreditation_slug: str | None,
        difficulty: DifficultyLevel | None,
        search: str | None,
    ) -> list[ColumnElement[bool]]:
        """Build the filter list shared by the page query and its count."""
        conditions: list[ColumnElement[bool]] = [Course.status == CourseStatus.PUBLISHED]
        if specialization_slug is not None:
            conditions.append(Specialization.slug == specialization_slug)
        if accreditation_slug is not None:
            conditions.append(Accreditation.slug == accreditation_slug)
        if difficulty is not None:
            conditions.append(Course.difficulty == difficulty)
        if search:
            conditions.append(Course.title.ilike(f"%{search}%"))
        return conditions
