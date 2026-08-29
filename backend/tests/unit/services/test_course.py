"""Catalogue paging rules and the course page."""

import pytest

from models.enums import Audience
from services.course import MAX_PAGE_SIZE, CourseNotFoundError, CourseService
from tests.support.factories import make_benefit, make_course, make_specialization
from tests.support.fakes import FakeBenefitRepo, FakeCourseRepo


async def test_page_two_skips_the_first_page() -> None:
    """Offset is derived from the page number: an off-by-one here silently hides a course."""
    courses = [make_course(slug=f"course-{index}", title=f"Course {index}") for index in range(5)]
    service = CourseService(course_repo=FakeCourseRepo(courses), benefit_repo=FakeBenefitRepo())

    page = await service.list_catalog(page=2, size=2)

    assert [item.slug for item in page.items] == ["course-2", "course-3"]
    assert page.total == 5


async def test_oversized_page_is_clamped() -> None:
    """A caller asking for a thousand rows gets the cap, not a thousand rows."""
    service = CourseService(course_repo=FakeCourseRepo([]), benefit_repo=FakeBenefitRepo())

    page = await service.list_catalog(size=1000)

    assert page.size == MAX_PAGE_SIZE


async def test_filters_reach_the_repository() -> None:
    """Every control on the filter bar has to survive the trip to the query."""
    palliative = make_specialization(
        slug="palliative-care", name="Palliative care", audience=Audience.NURSE
    )
    courses = [
        make_course(slug="palliative-care", title="Palliative care", specialization=palliative),
        make_course(slug="therapy", title="Therapy"),
    ]
    service = CourseService(course_repo=FakeCourseRepo(courses), benefit_repo=FakeBenefitRepo())

    page = await service.list_catalog(
        specialization_slug="palliative-care", audience=Audience.NURSE
    )

    assert [item.slug for item in page.items] == ["palliative-care"]


async def test_a_course_page_is_served_by_slug() -> None:
    """The page asks by slug, so the slug has to reach storage unchanged."""
    service = CourseService(
        course_repo=FakeCourseRepo([make_course(slug="therapy")]),
        benefit_repo=FakeBenefitRepo([make_benefit(title="Convenient format")]),
    )

    course = await service.get_course(slug="therapy")

    assert course.slug == "therapy"
    assert [item.title for item in course.benefits] == ["Convenient format"]


async def test_an_unknown_slug_is_not_a_course() -> None:
    """An empty page would look like a course with nothing in it; this has to fail loudly."""
    service = CourseService(course_repo=FakeCourseRepo([]), benefit_repo=FakeBenefitRepo())

    with pytest.raises(CourseNotFoundError):
        await service.get_course(slug="does-not-exist")
