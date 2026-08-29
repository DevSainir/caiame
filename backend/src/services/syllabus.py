from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, UnitStatus
from schemas.syllabus import CourseUnitOut, SyllabusOut
from services.course import CourseNotFoundError


class CourseLookup(Protocol):
    """The one thing the outline needs from the course storage."""

    async def get_published_by_slug(self, slug: str) -> Course | None:
        """Return one published course, or nothing."""
        ...


class SyllabusReader(Protocol):
    """What the outline needs from storage."""

    async def list_units(self, course_id: UUID) -> Sequence[CourseUnit]:
        """Every module and work of one course, in display order."""
        ...

    async def statuses_for(self, *, user_id: UUID, course_id: UUID) -> dict[UUID, str]:
        """One student's status per unit."""
        ...


class SyllabusService:
    """The course outline and the progress derived from it."""

    def __init__(self, *, course_repo: CourseLookup, syllabus_repo: SyllabusReader) -> None:
        self.course_repo = course_repo
        self.syllabus_repo = syllabus_repo

    async def get_syllabus(self, *, slug: str, user_id: UUID | None) -> SyllabusOut:
        """
        The outline of one course, with the asking account's own progress.

        A visitor without an account sees the same outline with every unit not started:
        the list of modules is public, what somebody did with them is not.
        """
        course = await self.course_repo.get_published_by_slug(slug)
        if course is None:
            raise CourseNotFoundError(slug)

        units = await self.syllabus_repo.list_units(course.id)
        statuses = (
            await self.syllabus_repo.statuses_for(user_id=user_id, course_id=course.id)
            if user_id is not None
            else {}
        )
        items = [self._to_out(unit, statuses) for unit in units]
        return SyllabusOut(
            modules=[item for item in items if item.kind is CourseUnitKind.MODULE],
            activities=[item for item in items if item.kind is not CourseUnitKind.MODULE],
            progress_percent=self._percent(items),
        )

    @staticmethod
    def _to_out(unit: CourseUnit, statuses: dict[UUID, str]) -> CourseUnitOut:
        """Attach the viewer's status to a unit; anything unknown is «not started»."""
        raw = statuses.get(unit.id)
        return CourseUnitOut(
            id=unit.id,
            kind=unit.kind,
            position=unit.position,
            title=unit.title,
            summary=unit.summary,
            status=UnitStatus(raw) if raw is not None else UnitStatus.NOT_STARTED,
        )

    @staticmethod
    def _percent(items: list[CourseUnitOut]) -> int:
        """
        Share of the course that is finished.

        Counted from the facts on every call, never stored. A unit in progress counts for
        nothing here: a half-watched lesson is not a passed one, and giving it half a point
        is how a course reaches 100% without being finished.
        """
        if not items:
            return 0
        done = sum(1 for item in items if item.status is UnitStatus.DONE)
        return round(done * 100 / len(items))
