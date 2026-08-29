from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.review import Review


class ReviewRepo:
    """Data access for course reviews."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def page(
        self, *, course_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Review], int]:
        """One page of reviews, newest first, with the total behind it."""
        total: int | None = await self.session.scalar(
            select(func.count(Review.id)).where(Review.course_id == course_id)
        )
        rows = await self.session.scalars(
            select(Review)
            .where(Review.course_id == course_id)
            .options(selectinload(Review.author))
            .order_by(Review.created_at.desc(), Review.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return rows.all(), total or 0

    async def counts_by_rating(self, course_id: UUID) -> dict[int, int]:
        """How many reviews gave each of the five ratings — the histogram, unrounded."""
        rows = await self.session.execute(
            select(Review.rating, func.count(Review.id))
            .where(Review.course_id == course_id)
            .group_by(Review.rating)
        )
        return {int(rating): int(count) for rating, count in rows.all()}
