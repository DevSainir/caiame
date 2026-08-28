from collections.abc import Sequence
from typing import Protocol

from models.course import Course
from models.enums import DifficultyLevel
from schemas.course import CourseOut, CoursePageOut

MAX_PAGE_SIZE = 48


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
        difficulty: DifficultyLevel | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Course], int]:
        """Return one page of published courses and the total number that match."""
        ...


class CourseService:
    """Application rules for the course catalogue."""

    def __init__(self, *, course_repo: CourseReader) -> None:
        self.course_repo = course_repo

    async def list_catalog(
        self,
        *,
        specialization_slug: str | None = None,
        accreditation_slug: str | None = None,
        difficulty: DifficultyLevel | None = None,
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
            difficulty=difficulty,
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
