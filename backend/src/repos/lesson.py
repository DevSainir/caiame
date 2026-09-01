from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, func, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.course_unit import CourseUnit
from models.enums import UnitStatus
from models.lesson import Lesson
from models.lesson_progress import LessonProgress


class LessonRepo:
    """Data access for lessons and for one student's facts about them."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, lesson_id: UUID) -> Lesson | None:
        """One lesson that has not been removed from the course."""
        lesson: Lesson | None = await self.session.scalar(
            select(Lesson).where(Lesson.id == lesson_id, Lesson.deleted_at.is_(None))
        )
        return lesson

    async def list_for_unit(self, unit_id: UUID) -> Sequence[Lesson]:
        """Every lesson of one module, in the order they are studied."""
        rows = await self.session.scalars(
            select(Lesson)
            .where(Lesson.unit_id == unit_id, Lesson.deleted_at.is_(None))
            .order_by(Lesson.position)
        )
        return rows.all()

    async def list_for_course(self, course_id: UUID) -> Sequence[Lesson]:
        """
        Every lesson of every module of one course.

        Deleted lessons are left out here too: they must disappear from the denominator of
        the percentage without disappearing from anybody's history.
        """
        rows = await self.session.scalars(
            select(Lesson)
            .join(CourseUnit, CourseUnit.id == Lesson.unit_id)
            .where(CourseUnit.course_id == course_id, Lesson.deleted_at.is_(None))
            .order_by(Lesson.position)
        )
        return rows.all()

    async def statuses_for_course(self, *, user_id: UUID, course_id: UUID) -> dict[UUID, str]:
        """One student's status per lesson of one course, as a lookup keyed by lesson."""
        rows = await self.session.execute(
            select(LessonProgress.lesson_id, LessonProgress.status)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .join(CourseUnit, CourseUnit.id == Lesson.unit_id)
            .where(LessonProgress.user_id == user_id, CourseUnit.course_id == course_id)
        )
        return {lesson_id: str(status) for lesson_id, status in rows.all()}

    async def required_totals(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """How many required lectures each course has — the denominator of its percentage."""
        if not course_ids:
            return {}
        rows = await self.session.execute(
            select(CourseUnit.course_id, func.count(Lesson.id))
            .join(Lesson, Lesson.unit_id == CourseUnit.id)
            .where(
                CourseUnit.course_id.in_(course_ids),
                Lesson.deleted_at.is_(None),
                Lesson.is_required.is_(True),
            )
            .group_by(CourseUnit.course_id)
        )
        return {course_id: int(count) for course_id, count in rows.all()}

    async def done_by_student(
        self, *, course_ids: Sequence[UUID], user_ids: Sequence[UUID]
    ) -> dict[tuple[UUID, UUID], int]:
        """
        Finished required lectures per student and course, for a whole page of students.

        One query rather than one per row: the administration list shows twenty students at
        a time, and twenty round trips to draw one column is how a screen becomes slow for
        no reason anybody can see.
        """
        if not course_ids or not user_ids:
            return {}
        rows = await self.session.execute(
            select(LessonProgress.user_id, CourseUnit.course_id, func.count(LessonProgress.id))
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .join(CourseUnit, CourseUnit.id == Lesson.unit_id)
            .where(
                LessonProgress.user_id.in_(user_ids),
                CourseUnit.course_id.in_(course_ids),
                LessonProgress.status == UnitStatus.DONE,
                Lesson.deleted_at.is_(None),
                Lesson.is_required.is_(True),
            )
            .group_by(LessonProgress.user_id, CourseUnit.course_id)
        )
        return {(user_id, course_id): int(count) for user_id, course_id, count in rows.all()}

    async def get_progress(self, *, user_id: UUID, lesson_id: UUID) -> LessonProgress | None:
        """One student's row for one lesson, if there is one yet."""
        progress: LessonProgress | None = await self.session.scalar(
            select(LessonProgress).where(
                LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id
            )
        )
        return progress

    async def record_playback(
        self, *, user_id: UUID, lesson_id: UUID, position_sec: int, watched_delta: int
    ) -> LessonProgress:
        """
        Add played time to a lesson and remember where the student is.

        An upsert rather than «read, add, write»: a player sends these while the page is
        being closed, and two events in flight would otherwise overwrite each other and
        lose the seconds one of them carried. The addition happens in the database, where
        it cannot race with itself.
        """
        insertion = insert(LessonProgress).values(
            user_id=user_id,
            lesson_id=lesson_id,
            status=UnitStatus.IN_PROGRESS,
            last_position_sec=position_sec,
            watched_seconds=watched_delta,
        )
        statement = insertion.on_conflict_do_update(
            index_elements=[LessonProgress.user_id, LessonProgress.lesson_id],
            set_={
                "last_position_sec": position_sec,
                "watched_seconds": LessonProgress.watched_seconds + watched_delta,
                # A finished lesson stays finished: rewatching does not undo it.
                #
                # The two results are wrapped in `literal` with the column's own type on
                # purpose. Without it SQLAlchemy binds the enum by its value and writes
                # «in_progress» into a column that stores member names — the row goes in
                # and every later read of it raises.
                "status": case(
                    (
                        LessonProgress.status == UnitStatus.DONE,
                        literal(UnitStatus.DONE, LessonProgress.status.type),
                    ),
                    else_=literal(UnitStatus.IN_PROGRESS, LessonProgress.status.type),
                ),
            },
        ).returning(LessonProgress)
        # `scalar_one` rather than a nullable read: an upsert with RETURNING always gives
        # back exactly one row, and pretending it might not adds a branch nothing can reach.
        result = await self.session.execute(statement)
        progress: LessonProgress = result.scalar_one()
        return progress

    async def mark_completed(self, *, user_id: UUID, lesson_id: UUID) -> None:
        """
        Record that a student finished a lesson.

        An upsert that leaves `completed_at` alone on conflict: the client sends this on
        every return to the page and on every double click, and all of them are the same
        event. Moving the timestamp would make «when did they finish» mean «when did they
        last look».
        """
        statement = insert(LessonProgress).values(
            user_id=user_id,
            lesson_id=lesson_id,
            status=UnitStatus.DONE,
            completed_at=datetime.now(UTC),
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[LessonProgress.user_id, LessonProgress.lesson_id],
                set_={"status": UnitStatus.DONE},
                where=LessonProgress.status != UnitStatus.DONE,
            )
        )
