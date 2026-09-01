"""
Who checks the work of a course.

Administration side of one small table. It exists because the question a reviewer screen
asks is «which courses», not «is this person staff»: the rung says they may review, the
assignment says whose work.
"""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.course_reviewer import CourseReviewer
from models.enums import UserRole
from models.user import User
from schemas.admin import ReviewerRowOut


class CourseNotFoundForReviewersError(Exception):
    """No such course."""


class NotStaffError(Exception):
    """The account exists but does not work here, so it cannot be put on a course."""


class ReviewerNotFoundError(Exception):
    """No such assignment on this course."""


class CourseLookup(Protocol):
    """Courses, drafts included."""

    async def get_course(self, course_id: UUID) -> Course | None: ...


class PeopleLookup(Protocol):
    """Accounts by address."""

    async def get_by_email(self, email: str) -> User | None: ...


class AssignmentStore(Protocol):
    """The table of «who checks which course»."""

    async def list_for_course(self, course_id: UUID) -> Sequence[tuple[CourseReviewer, User]]: ...
    async def get(self, assignment_id: UUID) -> CourseReviewer | None: ...
    async def add(self, *, course_id: UUID, user_id: UUID) -> CourseReviewer: ...
    async def remove(self, assignment: CourseReviewer) -> None: ...
    async def exists(self, *, course_id: UUID, user_id: UUID) -> bool: ...


class ReviewerService:
    """Putting people on courses and taking them off."""

    def __init__(
        self, *, course_repo: CourseLookup, people: PeopleLookup, assignments: AssignmentStore
    ) -> None:
        self.course_repo = course_repo
        self.people = people
        self.assignments = assignments

    async def list_reviewers(self, course_id: UUID) -> list[ReviewerRowOut]:
        """Who checks the work of this course."""
        await self._course(course_id)
        return [
            ReviewerRowOut(
                id=assignment.id,
                user_id=person.id,
                name=person.full_name,
                email=person.email,
                role=person.role,
            )
            for assignment, person in await self.assignments.list_for_course(course_id)
        ]

    async def add_reviewer(self, *, course_id: UUID, email: str) -> list[ReviewerRowOut]:
        """
        Put somebody on a course by the address they signed in with.

        Only staff: a student put on a course would be reading their coursemates' work, and
        the refusal here is the only thing between a mistyped address and exactly that.
        Adding the same person twice changes nothing.
        """
        course = await self._course(course_id)
        person = await self.people.get_by_email(email.strip().lower())
        if person is None or person.role is UserRole.STUDENT:
            raise NotStaffError(email)
        if not await self.assignments.exists(course_id=course.id, user_id=person.id):
            await self.assignments.add(course_id=course.id, user_id=person.id)
        return await self.list_reviewers(course_id)

    async def remove_reviewer(
        self, *, course_id: UUID, assignment_id: UUID
    ) -> list[ReviewerRowOut]:
        """
        Take somebody off a course.

        The reviews they already wrote stay where they are: a verdict a student has read
        does not stop having been given because its author moved to another course.
        """
        await self._course(course_id)
        assignment = await self.assignments.get(assignment_id)
        if assignment is None or assignment.course_id != course_id:
            raise ReviewerNotFoundError(assignment_id)
        await self.assignments.remove(assignment)
        return await self.list_reviewers(course_id)

    async def _course(self, course_id: UUID) -> Course:
        """The course, or a refusal that says nothing about what exists."""
        course = await self.course_repo.get_course(course_id)
        if course is None:
            raise CourseNotFoundForReviewersError(course_id)
        return course
