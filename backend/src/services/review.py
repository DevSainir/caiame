from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.review import Review
from schemas.review import RatingBarOut, RatingSummaryOut, ReviewOut, ReviewPageOut
from services.course import CourseNotFoundError

MAX_PAGE_SIZE = 20
RATINGS = (5, 4, 3, 2, 1)


class CourseLookup(Protocol):
    """The one thing the review list needs from the course storage."""

    async def get_published_by_slug(self, slug: str) -> Course | None:
        """Return one published course, or nothing."""
        ...


class ReviewReader(Protocol):
    """What the review list needs from storage."""

    async def page(
        self, *, course_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Review], int]:
        """One page of reviews and the total behind it."""
        ...

    async def counts_by_rating(self, course_id: UUID) -> dict[int, int]:
        """How many reviews gave each rating."""
        ...


class ReviewService:
    """Reviews of one course, page by page, with their summary."""

    def __init__(self, *, course_repo: CourseLookup, review_repo: ReviewReader) -> None:
        self.course_repo = course_repo
        self.review_repo = review_repo

    async def list_for_course(self, *, slug: str, page: int = 1, size: int = 3) -> ReviewPageOut:
        """One page of reviews for a published course."""
        course = await self.course_repo.get_published_by_slug(slug)
        if course is None:
            raise CourseNotFoundError(slug)

        size = min(size, MAX_PAGE_SIZE)
        reviews, total = await self.review_repo.page(
            course_id=course.id, limit=size, offset=(page - 1) * size
        )
        counts = await self.review_repo.counts_by_rating(course.id)
        return ReviewPageOut(
            items=[
                ReviewOut(
                    id=review.id,
                    author_name=review.author.full_name,
                    rating=review.rating,
                    text=review.text,
                    created_at=review.created_at,
                )
                for review in reviews
            ],
            total=total,
            page=page,
            size=size,
            summary=self._summary(counts),
        )

    @staticmethod
    def _summary(counts: dict[int, int]) -> RatingSummaryOut:
        """
        Average and histogram from the grouped counts.

        Computed from every review of the course and not from the page: a summary that
        described only the three reviews on screen would change as the reader pages.
        """
        total = sum(counts.values())
        if total == 0:
            return RatingSummaryOut(
                average=0.0,
                count=0,
                histogram=[RatingBarOut(stars=stars, percent=0) for stars in RATINGS],
            )
        average = sum(stars * count for stars, count in counts.items()) / total
        return RatingSummaryOut(
            average=round(average, 1),
            count=total,
            histogram=[
                RatingBarOut(stars=stars, percent=round(counts.get(stars, 0) * 100 / total))
                for stars in RATINGS
            ],
        )
