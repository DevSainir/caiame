from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.course_reviewer import CourseReviewer
from models.user import User


class ReviewerRepo:
    """Data access for who checks the work of which course."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def course_ids_for(self, user_id: UUID) -> list[UUID]:
        """Every course this person was put on. Empty means «none», never «all»."""
        rows = await self.session.scalars(
            select(CourseReviewer.course_id).where(CourseReviewer.user_id == user_id)
        )
        return list(rows.all())

    async def list_for_course(self, course_id: UUID) -> list[tuple[CourseReviewer, User]]:
        """Reviewers of one course together with their accounts."""
        rows = await self.session.execute(
            select(CourseReviewer, User)
            .join(User, User.id == CourseReviewer.user_id)
            .where(CourseReviewer.course_id == course_id)
            .order_by(User.full_name)
        )
        return [(assignment, person) for assignment, person in rows.all()]

    async def get(self, assignment_id: UUID) -> CourseReviewer | None:
        """One assignment by its id."""
        assignment: CourseReviewer | None = await self.session.get(CourseReviewer, assignment_id)
        return assignment

    async def add(self, *, course_id: UUID, user_id: UUID) -> CourseReviewer:
        """Put somebody on a course."""
        assignment = CourseReviewer(course_id=course_id, user_id=user_id)
        self.session.add(assignment)
        await self.session.flush()
        return assignment

    async def remove(self, assignment: CourseReviewer) -> None:
        """Take somebody off a course. The reviews they wrote stay where they are."""
        await self.session.delete(assignment)

    async def exists(self, *, course_id: UUID, user_id: UUID) -> bool:
        """Whether this person is already on this course."""
        found = await self.session.scalar(
            select(CourseReviewer.id).where(
                CourseReviewer.course_id == course_id, CourseReviewer.user_id == user_id
            )
        )
        return found is not None
