from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.course_benefit import CourseBenefit
from models.enums import Audience
from schemas.course import BenefitOut, CourseDetailOut, CourseOut, CoursePageOut

MAX_PAGE_SIZE = 48


class CourseNotFoundError(Exception):
    """No published course answers to this slug."""


class CourseReader(Protocol):
    """
    What the catalogue needs from storage.

    Declared as a protocol rather than the concrete repository so the hand-written fake in
    the tests satisfies the same contract the real class does — a fake that does not
    type-check is a fake that drifts away from the thing it replaces.
    """

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
        """Return one page of published courses and the total number that match."""
        ...

    async def get_published_by_slug(self, slug: str) -> Course | None:
        """Return one published course, or nothing."""
        ...


class BenefitReader(Protocol):
    """What the course page needs from the reasons storage."""

    async def list_for_course(self, course_id: UUID) -> Sequence[CourseBenefit]:
        """Every reason listed under one course, in display order."""
        ...


class CourseService:
    """Application rules for the course catalogue."""

    def __init__(self, *, course_repo: CourseReader, benefit_repo: BenefitReader) -> None:
        self.course_repo = course_repo
        self.benefit_repo = benefit_repo

    async def list_catalog(
        self,
        *,
        specialization_slug: str | None = None,
        accreditation_slug: str | None = None,
        audience: Audience | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 12,
    ) -> CoursePageOut:
        """
        List published courses for the public catalogue.

        Draft and archived courses are invisible here by construction rather than by a flag
        the caller may forget: the repository only ever selects published rows.
        """
        size = min(size, MAX_PAGE_SIZE)
        courses, total = await self.course_repo.list_published(
            specialization_slug=specialization_slug,
            accreditation_slug=accreditation_slug,
            audience=audience,
            search=search,
            limit=size,
            offset=(page - 1) * size,
        )
        return CoursePageOut(
            items=[CourseOut.model_validate(course) for course in courses],
            total=total,
            page=page,
            size=size,
        )

    async def get_course(self, *, slug: str) -> CourseDetailOut:
        """
        One course for its own page.

        A draft, an archived course and a slug that never existed answer the same way: the
        catalogue must not become a way to find out what is being written but not published.
        """
        course = await self.course_repo.get_published_by_slug(slug)
        if course is None:
            raise CourseNotFoundError(slug)
        benefits = await self.benefit_repo.list_for_course(course.id)
        return CourseDetailOut(
            **CourseOut.model_validate(course).model_dump(),
            description=course.description,
            benefits=[BenefitOut.model_validate(item) for item in benefits],
        )
