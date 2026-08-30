from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, UnitStatus
from models.lesson import Lesson
from schemas.syllabus import CourseUnitOut, SyllabusOut
from services.course import CourseNotFoundError
from services.learning import module_status, status_of


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


class LessonReader(Protocol):
    """What the outline needs from the lesson storage."""

    async def list_for_course(self, course_id: UUID) -> Sequence[Lesson]:
        """Every live lesson of one course."""
        ...

    async def statuses_for_course(self, *, user_id: UUID, course_id: UUID) -> dict[UUID, str]:
        """One student's status per lesson of one course."""
        ...


class SyllabusService:
    """The course outline and the progress derived from it."""

    def __init__(
        self,
        *,
        course_repo: CourseLookup,
        syllabus_repo: SyllabusReader,
        lesson_repo: LessonReader,
    ) -> None:
        self.course_repo = course_repo
        self.syllabus_repo = syllabus_repo
        self.lesson_repo = lesson_repo

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
        lessons = await self.lesson_repo.list_for_course(course.id)
        unit_statuses = (
            await self.syllabus_repo.statuses_for(user_id=user_id, course_id=course.id)
            if user_id is not None
            else {}
        )
        lesson_statuses = (
            await self.lesson_repo.statuses_for_course(user_id=user_id, course_id=course.id)
            if user_id is not None
            else {}
        )

        by_unit: dict[UUID, list[Lesson]] = {}
        for lesson in lessons:
            by_unit.setdefault(lesson.unit_id, []).append(lesson)

        items = [
            self._to_out(unit, unit_statuses, by_unit.get(unit.id, []), lesson_statuses)
            for unit in units
        ]
        return SyllabusOut(
            modules=[item for item in items if item.kind is CourseUnitKind.MODULE],
            activities=[item for item in items if item.kind is not CourseUnitKind.MODULE],
            progress_percent=self._percent(items, lessons, lesson_statuses),
        )

    @staticmethod
    def _to_out(
        unit: CourseUnit,
        unit_statuses: dict[UUID, str],
        lessons: Sequence[Lesson],
        lesson_statuses: dict[UUID, str],
    ) -> CourseUnitOut:
        """
        Attach the viewer's status to a line of the outline.

        A module has no status of its own — it is a container, and its row shows what its
        lectures add up to. A second stored «done» here would be a second place to disagree
        with them.
        """
        status = (
            module_status(lessons, lesson_statuses)
            if unit.kind is CourseUnitKind.MODULE
            else status_of(unit.id, unit_statuses)
        )
        return CourseUnitOut(
            id=unit.id,
            kind=unit.kind,
            position=unit.position,
            title=unit.title,
            summary=unit.summary,
            status=status,
        )

    @staticmethod
    def _percent(
        items: list[CourseUnitOut],
        lessons: Sequence[Lesson],
        lesson_statuses: dict[UUID, str],
    ) -> int:
        """
        Share of the course that is finished.

        Counted on every call from the facts, never stored. Lectures and works are the
        atoms; modules are not counted twice for containing them. A lecture in progress
        earns nothing: half-watched is not passed, and half a point is how a course reaches
        100 % without being finished. Optional lectures stay out of the denominator, which
        is the safe way to add material to a course people are already taking.
        """
        required = [lesson for lesson in lessons if lesson.is_required]
        works = [item for item in items if item.kind is not CourseUnitKind.MODULE]
        total = len(required) + len(works)
        if total == 0:
            return 0
        done = sum(
            1 for lesson in required if status_of(lesson.id, lesson_statuses) is UnitStatus.DONE
        )
        done += sum(1 for work in works if work.status is UnitStatus.DONE)
        return round(done * 100 / total)
