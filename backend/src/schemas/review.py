from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReviewOut(BaseModel):
    """One review as the course page shows it."""

    id: UUID
    author_name: str
    rating: int
    text: str
    created_at: datetime


class RatingBarOut(BaseModel):
    """One bar of the rating histogram."""

    stars: int
    percent: int


class RatingSummaryOut(BaseModel):
    """The average, the count and the five bars — everything above the review list."""

    average: float
    count: int
    histogram: list[RatingBarOut]


class ReviewPageOut(BaseModel):
    """
    One page of reviews plus the summary of all of them.

    The summary rides along with every page on purpose: it is one grouped count, and asking
    for it separately would mean a second round-trip for a block that is always shown.
    """

    items: list[ReviewOut]
    total: int
    page: int
    size: int
    summary: RatingSummaryOut
