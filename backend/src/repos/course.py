from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.accreditation import Accreditation
from models.course import Course
from models.enums import Audience, CourseStatus
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
        audience: Audience | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Course], int]:
        """
        Return one page of published courses and the total number that match the filters.

        Ordered by the specialization's display position and not by creation date: the
        catalogue is a fixed curriculum shown in the order the academy lists it, so
        re-seeding a course must not move it to the front of the page.
        """
        conditions = self._conditions(
            specialization_slug=specialization_slug,
            accreditation_slug=accreditation_slug,
            audience=audience,
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
            .order_by(Specialization.position, Course.title, Course.id)
            .limit(limit)
            .offset(offset)
        )
        return rows.all(), total or 0

    async def list_published_slugs(self) -> Sequence[tuple[str, datetime]]:
        """
        Addresses of published courses and when each was last changed.

        Drafts and archived courses are left out: a sitemap is an invitation to visit, not
        an inventory of everything in the database.
        """
        rows = await self.session.execute(
            select(Course.slug, Course.updated_at)
            .where(Course.status == CourseStatus.PUBLISHED)
            .order_by(Course.title)
        )
        return [(slug, updated_at) for slug, updated_at in rows.all()]

    async def get_published_by_slug(self, slug: str) -> Course | None:
        """Return one published course with both taxonomies loaded, or nothing."""
        course: Course | None = await self.session.scalar(
            self._base_query().where(Course.status == CourseStatus.PUBLISHED, Course.slug == slug)
        )
        return course

    async def get_published_by_id(self, course_id: UUID) -> Course | None:
        """One published course by id — the way the lesson pages find their heading."""
        course: Course | None = await self.session.scalar(
            select(Course).where(Course.status == CourseStatus.PUBLISHED, Course.id == course_id)
        )
        return course

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
        audience: Audience | None,
        search: str | None,
    ) -> list[ColumnElement[bool]]:
        """Build the filter list shared by the page query and its count."""
        conditions: list[ColumnElement[bool]] = [Course.status == CourseStatus.PUBLISHED]
        if specialization_slug is not None:
            conditions.append(Specialization.slug == specialization_slug)
        if accreditation_slug is not None:
            conditions.append(Accreditation.slug == accreditation_slug)
        if audience is not None:
            conditions.append(Specialization.audience == audience)
        if search:
            conditions.append(Course.title.ilike(f"%{search}%"))
        return conditions
