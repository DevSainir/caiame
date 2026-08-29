"""Review pages and the rating summary above them."""

import pytest

from models.review import Review
from services.course import CourseNotFoundError
from services.review import ReviewService
from tests.support.factories import make_course, make_review
from tests.support.fakes import FakeCourseRepo, FakeReviewRepo


def _service(reviews: list[Review]) -> ReviewService:
    """A service over one published course and the reviews handed in."""
    course = make_course(slug="therapy")
    return ReviewService(course_repo=FakeCourseRepo([course]), review_repo=FakeReviewRepo(reviews))


async def test_the_summary_describes_every_review_not_the_page() -> None:
    """A summary that changed as the reader pages would be a bug nobody could explain."""
    reviews = [make_review(rating=5) for _ in range(3)] + [make_review(rating=4)]
    service = _service(reviews)

    page = await service.list_for_course(slug="therapy", page=1, size=2)

    assert len(page.items) == 2
    assert page.total == 4
    assert page.summary.count == 4
    assert page.summary.average == 4.8


async def test_the_histogram_covers_all_five_ratings() -> None:
    """The block draws five bars; a rating nobody gave still has to be one of them."""
    service = _service([make_review(rating=5), make_review(rating=4)])

    page = await service.list_for_course(slug="therapy")

    assert [bar.stars for bar in page.summary.histogram] == [5, 4, 3, 2, 1]
    assert [bar.percent for bar in page.summary.histogram] == [50, 50, 0, 0, 0]


async def test_a_course_without_reviews_answers_with_zeros() -> None:
    """No reviews is the first day of every course, not an error and not a division by zero."""
    service = _service([])

    page = await service.list_for_course(slug="therapy")

    assert page.items == []
    assert page.summary.count == 0
    assert page.summary.average == 0


async def test_reviews_of_an_unknown_course_are_a_failure() -> None:
    """An empty list would say the course exists and nobody wrote about it."""
    service = ReviewService(course_repo=FakeCourseRepo([]), review_repo=FakeReviewRepo([]))

    with pytest.raises(CourseNotFoundError):
        await service.list_for_course(slug="missing")
