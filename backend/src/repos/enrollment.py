from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.enrollment import Enrollment


class EnrollmentRepo:
    """Data access for study records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, *, user_id: UUID, course_id: UUID) -> Enrollment | None:
        """The study record of one student in one course, if there is one."""
        enrollment: Enrollment | None = await self.session.scalar(
            select(Enrollment).where(
                Enrollment.user_id == user_id, Enrollment.course_id == course_id
            )
        )
        return enrollment

    async def ensure(self, *, user_id: UUID, course_id: UUID, last_lesson_id: UUID | None) -> None:
        """
        Enrol a student, or leave the existing record exactly where it is.

        An insert that does nothing on conflict, rather than «select, then insert»: two
        lecture pages opened at once both pass a read check and one of them then breaks on
        the unique index. Only the last lesson moves on a repeat, so the «continue» button
        follows the student.
        """
        statement = insert(Enrollment).values(
            user_id=user_id,
            course_id=course_id,
            started_at=datetime.now(UTC),
            last_lesson_id=last_lesson_id,
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                constraint="uq_enrollment_student", set_={"last_lesson_id": last_lesson_id}
            )
        )

    async def count_for_course(self, course_id: UUID) -> int:
        """How many students are taking one course. Shown in the administration list."""
        rows = await self.session.scalars(
            select(Enrollment.id).where(Enrollment.course_id == course_id)
        )
        return len(rows.all())
