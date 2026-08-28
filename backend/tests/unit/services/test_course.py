"""Catalogue paging rules."""

from models.enums import DifficultyLevel
from services.course import MAX_PAGE_SIZE, CourseService
from tests.support.factories import make_course, make_specialization
from tests.support.fakes import FakeCourseRepo


async def test_page_two_skips_the_first_page() -> None:
    """Offset is derived from the page number: an off-by-one here silently hides a course."""
    courses = [make_course(slug=f"course-{index}", title=f"Course {index}") for index in range(5)]
    service = CourseService(course_repo=FakeCourseRepo(courses))

    page = await service.list_catalog(page=2, size=2)

    assert [item.slug for item in page.items] == ["course-2", "course-3"]
    assert page.total == 5


async def test_oversized_page_is_clamped() -> None:
    """A caller asking for a thousand rows gets the cap, not a thousand rows."""
    service = CourseService(course_repo=FakeCourseRepo([]))

    page = await service.list_catalog(size=1000)

    assert page.size == MAX_PAGE_SIZE


async def test_filters_reach_the_repository() -> None:
    """Every control on the filter bar has to survive the trip to the query."""
    neurology = make_specialization(slug="neurology", name="Neurology")
    courses = [
        make_course(
            slug="stroke",
            title="Stroke",
            specialization=neurology,
            difficulty=DifficultyLevel.ADVANCED,
        ),
        make_course(slug="acs", title="Acute coronary syndrome"),
    ]
    service = CourseService(course_repo=FakeCourseRepo(courses))

    page = await service.list_catalog(
        specialization_slug="neurology", difficulty=DifficultyLevel.ADVANCED
    )

    assert [item.slug for item in page.items] == ["stroke"]
