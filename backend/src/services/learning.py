from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, LessonKind, UnitStatus
from models.lesson import Lesson
from schemas.learning import (
    CourseRefOut,
    LessonDetailOut,
    LessonRowOut,
    LessonStatusOut,
    ModuleDetailOut,
    ModuleRefOut,
)


class LessonNotFoundError(Exception):
    """No such lesson, or it is not a lesson this student may open."""


class ModuleNotFoundError(Exception):
    """No such module in any published course."""


class CourseByIdReader(Protocol):
    """What the lesson pages need from the course storage."""

    async def get_published_by_id(self, course_id: UUID) -> Course | None:
        """Return one published course by its id, or nothing."""
        ...


class UnitReader(Protocol):
    """What the lesson pages need from the outline storage."""

    async def get_unit(self, unit_id: UUID) -> CourseUnit | None:
        """One line of the outline by its id."""
        ...


class LessonReader(Protocol):
    """What the lesson pages need from the lesson storage."""

    async def get(self, lesson_id: UUID) -> Lesson | None:
        """One live lesson."""
        ...

    async def list_for_unit(self, unit_id: UUID) -> Sequence[Lesson]:
        """Every lesson of one module, in study order."""
        ...

    async def statuses_for_course(self, *, user_id: UUID, course_id: UUID) -> dict[UUID, str]:
        """One student's status per lesson of one course."""
        ...

    async def mark_completed(self, *, user_id: UUID, lesson_id: UUID) -> None:
        """Record that a student finished a lesson."""
        ...


def completion_is_the_students_to_declare(kind: LessonKind) -> bool:
    """
    Whether pressing «finished» is what closes a lesson of this kind.

    The rule per kind lives here and in no `if` anywhere else. Today both kinds are closed
    by the student saying so; when watched time starts being counted (see `media-video`),
    video moves to «watched 90 % of the length» and only this function changes.
    """
    return kind in (LessonKind.VIDEO, LessonKind.PDF)


class LearningService:
    """The module page, the lecture page and the mark that closes a lecture."""

    def __init__(
        self,
        *,
        course_repo: CourseByIdReader,
        unit_repo: UnitReader,
        lesson_repo: LessonReader,
    ) -> None:
        self.course_repo = course_repo
        self.unit_repo = unit_repo
        self.lesson_repo = lesson_repo

    async def get_module(self, *, unit_id: UUID, user_id: UUID | None) -> ModuleDetailOut:
        """One module with its lectures and the asking student's progress in them."""
        unit = await self.unit_repo.get_unit(unit_id)
        if unit is None or unit.kind is not CourseUnitKind.MODULE:
            raise ModuleNotFoundError(unit_id)
        course = await self.course_repo.get_published_by_id(unit.course_id)
        if course is None:
            raise ModuleNotFoundError(unit_id)

        lessons = await self.lesson_repo.list_for_unit(unit.id)
        statuses = await self._statuses(user_id=user_id, course_id=course.id)
        return ModuleDetailOut(
            id=unit.id,
            title=unit.title,
            summary=unit.summary,
            description=unit.summary,
            course=CourseRefOut.model_validate(course),
            lessons=[
                LessonRowOut(
                    id=lesson.id,
                    position=lesson.position,
                    title=lesson.title,
                    kind=lesson.kind,
                    duration_minutes=lesson.duration_minutes,
                    status=status_of(lesson.id, statuses),
                )
                for lesson in lessons
            ],
        )

    async def get_lesson(self, *, lesson_id: UUID, user_id: UUID | None) -> LessonDetailOut:
        """One lecture with the context the page shows above it."""
        lesson = await self.lesson_repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFoundError(lesson_id)
        unit = await self.unit_repo.get_unit(lesson.unit_id)
        if unit is None:
            raise LessonNotFoundError(lesson_id)
        course = await self.course_repo.get_published_by_id(unit.course_id)
        if course is None:
            raise LessonNotFoundError(lesson_id)

        statuses = await self._statuses(user_id=user_id, course_id=course.id)
        return LessonDetailOut(
            id=lesson.id,
            title=lesson.title,
            description=lesson.description,
            kind=lesson.kind,
            duration_minutes=lesson.duration_minutes,
            asset_url=lesson.asset_url,
            status=status_of(lesson.id, statuses),
            course=CourseRefOut.model_validate(course),
            module=ModuleRefOut(id=unit.id, title=unit.title),
        )

    async def complete_lesson(self, *, lesson_id: UUID, user_id: UUID) -> LessonStatusOut:
        """
        Mark a lecture finished for this student.

        Idempotent: the page sends it on every return and on every double click, and all of
        them are one event. A lesson that is already finished stays finished with the time
        it was first finished at.
        """
        lesson = await self.lesson_repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFoundError(lesson_id)
        await self.lesson_repo.mark_completed(user_id=user_id, lesson_id=lesson_id)
        return LessonStatusOut(status=UnitStatus.DONE)

    async def _statuses(self, *, user_id: UUID | None, course_id: UUID) -> dict[UUID, str]:
        """One student's lesson statuses, or nothing at all for a visitor without a session."""
        if user_id is None:
            return {}
        return await self.lesson_repo.statuses_for_course(user_id=user_id, course_id=course_id)


def status_of(lesson_id: UUID, statuses: dict[UUID, str]) -> UnitStatus:
    """The stored status of a lesson; anything unknown has not been started."""
    raw = statuses.get(lesson_id)
    return UnitStatus(raw) if raw is not None else UnitStatus.NOT_STARTED


def module_status(lessons: Sequence[Lesson], statuses: dict[UUID, str]) -> UnitStatus:
    """
    What a module's row on the course page shows.

    Derived from its lectures rather than stored: a module is a container, and a second
    place to write «done» is a second place to disagree with the lectures themselves.
    """
    if not lessons:
        return UnitStatus.NOT_STARTED
    marks = [status_of(lesson.id, statuses) for lesson in lessons]
    if all(mark is UnitStatus.DONE for mark in marks):
        return UnitStatus.DONE
    if any(mark is not UnitStatus.NOT_STARTED for mark in marks):
        return UnitStatus.IN_PROGRESS
    return UnitStatus.NOT_STARTED
