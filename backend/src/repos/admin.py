from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.course import Course
from models.course_unit import CourseUnit
from models.enrollment import Enrollment
from models.enums import CourseStatus, CourseUnitKind
from models.lesson import Lesson


class AdminRepo:
    """
    Data access for the administration: everything the catalogue deliberately hides.

    Separate from `CourseRepo` because the difference is exactly one condition, and it is
    the dangerous one: this repository sees drafts. Keeping the two apart means a public
    query can never accidentally inherit that.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_courses(self) -> Sequence[Course]:
        """
        Every course of the academy, drafts included, in display order.

        The specialization is loaded up front: relations are declared `lazy="raise"`, so a
        missing eager load fails here rather than firing a query inside the serializer.
        """
        rows = await self.session.scalars(
            select(Course).options(selectinload(Course.specialization)).order_by(Course.title)
        )
        return rows.all()

    async def get_course(self, course_id: UUID) -> Course | None:
        """One course by id, whatever its status."""
        course: Course | None = await self.session.scalar(
            select(Course).where(Course.id == course_id)
        )
        return course

    async def count_units(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """How many modules each course has — one query for the whole list."""
        if not course_ids:
            return {}
        rows = await self.session.execute(
            select(CourseUnit.course_id, func.count(CourseUnit.id))
            .where(CourseUnit.course_id.in_(course_ids), CourseUnit.kind == CourseUnitKind.MODULE)
            .group_by(CourseUnit.course_id)
        )
        return {course_id: int(count) for course_id, count in rows.all()}

    async def count_lessons(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """How many live lectures each course has — deleted ones are not counted."""
        if not course_ids:
            return {}
        rows = await self.session.execute(
            select(CourseUnit.course_id, func.count(Lesson.id))
            .join(Lesson, Lesson.unit_id == CourseUnit.id)
            .where(CourseUnit.course_id.in_(course_ids), Lesson.deleted_at.is_(None))
            .group_by(CourseUnit.course_id)
        )
        return {course_id: int(count) for course_id, count in rows.all()}

    async def count_students(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """How many students are taking each course — one query for the whole list."""
        if not course_ids:
            return {}
        rows = await self.session.execute(
            select(Enrollment.course_id, func.count(Enrollment.id))
            .where(Enrollment.course_id.in_(course_ids))
            .group_by(Enrollment.course_id)
        )
        return {course_id: int(count) for course_id, count in rows.all()}

    async def slug_taken(self, slug: str, *, except_id: UUID | None = None) -> bool:
        """Whether another course already lives at this address."""
        statement = select(Course.id).where(Course.slug == slug)
        if except_id is not None:
            statement = statement.where(Course.id != except_id)
        return await self.session.scalar(statement.limit(1)) is not None

    async def add_course(self, course: Course) -> Course:
        """Insert a course and hand it back with its id."""
        self.session.add(course)
        await self.session.flush()
        return course

    async def delete_course(self, course: Course) -> None:
        """
        Erase a course entirely.

        Allowed by the service only for a draft nobody is taking. Everything below a course
        is cascaded away by the foreign keys, which is precisely why the condition above is
        not negotiable: on a published course this would take somebody's studying with it.
        """
        await self.session.delete(course)

    async def set_status(self, course: Course, status: CourseStatus) -> None:
        """Publish a course or take it out of the catalogue."""
        course.status = status

    async def add_unit(self, unit: CourseUnit) -> CourseUnit:
        """Insert a line of the programme and hand it back with its id."""
        self.session.add(unit)
        await self.session.flush()
        return unit

    async def next_position(self, *, course_id: UUID, kind: CourseUnitKind) -> int:
        """The position a new line takes: after the last one of its own kind."""
        last = await self.session.scalar(
            select(func.max(CourseUnit.position)).where(
                CourseUnit.course_id == course_id, CourseUnit.kind == kind
            )
        )
        return int(last or 0) + 1

    async def siblings(self, unit: CourseUnit) -> Sequence[CourseUnit]:
        """Lines of the same course and kind, in order — the row this one swaps with."""
        rows = await self.session.scalars(
            select(CourseUnit)
            .where(CourseUnit.course_id == unit.course_id, CourseUnit.kind == unit.kind)
            .order_by(CourseUnit.position)
        )
        return rows.all()

    async def delete_unit(self, unit: CourseUnit) -> None:
        """
        Remove a line of the programme.

        Physical deletion, unlike a lesson: nothing points at a module except its lessons,
        and those go with it by the foreign key. A module with lessons is refused a step
        above, in the service.
        """
        await self.session.delete(unit)

    async def add_lesson(self, lesson: Lesson) -> Lesson:
        """Insert a lecture and hand it back with its id."""
        self.session.add(lesson)
        await self.session.flush()
        return lesson

    async def next_lesson_position(self, unit_id: UUID) -> int:
        """The position a new lecture takes inside its module."""
        last = await self.session.scalar(
            select(func.max(Lesson.position)).where(Lesson.unit_id == unit_id)
        )
        return int(last or 0) + 1

    async def lesson_siblings(self, unit_id: UUID) -> Sequence[Lesson]:
        """Live lectures of one module, in order."""
        rows = await self.session.scalars(
            select(Lesson)
            .where(Lesson.unit_id == unit_id, Lesson.deleted_at.is_(None))
            .order_by(Lesson.position)
        )
        return rows.all()

    async def flush(self) -> None:
        """
        Push pending changes to the database now.

        Called after a reorder so a constraint violation surfaces inside the request. The
        session commits after the response has left, and a failure there would reach the
        log while the caller was told everything went fine.
        """
        await self.session.flush()

    async def soft_delete_lesson(self, lesson: Lesson) -> None:
        """
        Retire a lecture without erasing anybody's history.

        Progress rows, attempts and submitted work point at it. A hard delete either fails
        on the foreign key or, with a cascade, quietly removes what a student did.
        """
        lesson.deleted_at = datetime.now(UTC)
