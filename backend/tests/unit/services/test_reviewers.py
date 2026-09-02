"""
Who checks the work of a course.

One table, and one refusal that carries all the weight: a student put on a course by a
mistyped address would be reading their coursemates' work.
"""

from collections.abc import Sequence
from uuid import UUID

import pytest

from models.base import uuid7
from models.course import Course
from models.course_reviewer import CourseReviewer
from models.enums import UserRole
from models.user import User
from services.reviewers import (
    CourseNotFoundForReviewersError,
    NotStaffError,
    ReviewerNotFoundError,
    ReviewerService,
)
from tests.support.factories import make_course, make_user


class FakeCourses:
    """Courses by id, drafts included."""

    def __init__(self, course: Course | None) -> None:
        self.course = course

    async def get_course(self, course_id: UUID) -> Course | None:
        """The course, if this is the one."""
        if self.course is None or self.course.id != course_id:
            return None
        return self.course


class FakePeople:
    """Accounts by address, as the form looks them up."""

    def __init__(self, people: Sequence[User]) -> None:
        self.people = list(people)

    async def get_by_email(self, email: str) -> User | None:
        """Whoever signed in with this address."""
        return next((person for person in self.people if person.email == email), None)


class FakeAssignments:
    """The in-memory table of «who checks which course»."""

    def __init__(self, people: Sequence[User]) -> None:
        self.rows: list[CourseReviewer] = []
        self.people = list(people)

    async def list_for_course(self, course_id: UUID) -> Sequence[tuple[CourseReviewer, User]]:
        """Everyone put on this course, with their account."""
        by_id = {person.id: person for person in self.people}
        return [(row, by_id[row.user_id]) for row in self.rows if row.course_id == course_id]

    async def get(self, assignment_id: UUID) -> CourseReviewer | None:
        """One row by its id."""
        return next((row for row in self.rows if row.id == assignment_id), None)

    async def add(self, *, course_id: UUID, user_id: UUID) -> CourseReviewer:
        """Put somebody on a course."""
        row = CourseReviewer(id=uuid7(), course_id=course_id, user_id=user_id)
        self.rows.append(row)
        return row

    async def remove(self, assignment: CourseReviewer) -> None:
        """Take them off."""
        self.rows = [row for row in self.rows if row.id != assignment.id]

    async def exists(self, *, course_id: UUID, user_id: UUID) -> bool:
        """Whether they are already on it."""
        return any(row.course_id == course_id and row.user_id == user_id for row in self.rows)


def _service(
    *, people: Sequence[User] = (), course: Course | None = None
) -> tuple[ReviewerService, Course, FakeAssignments]:
    """A service over one course and the accounts these tests know about."""
    course = course or make_course(slug="ophthalmology", title="Офтальмология")
    assignments = FakeAssignments(people)
    service = ReviewerService(
        course_repo=FakeCourses(course), people=FakePeople(people), assignments=assignments
    )
    return service, course, assignments


async def test_a_teacher_is_put_on_a_course_by_their_address() -> None:
    """The address is what the person in the office has; the id is not."""
    teacher = make_user(email="teacher@example.org", role=UserRole.INSTRUCTOR)
    service, course, _ = _service(people=[teacher])

    rows = await service.add_reviewer(course_id=course.id, email="teacher@example.org")

    assert [row.email for row in rows] == ["teacher@example.org"]


async def test_the_address_is_read_the_way_it_was_typed_in() -> None:
    """Spaces and capitals come from a keyboard, not from a decision."""
    teacher = make_user(email="teacher@example.org", role=UserRole.INSTRUCTOR)
    service, course, _ = _service(people=[teacher])

    rows = await service.add_reviewer(course_id=course.id, email="  Teacher@Example.org ")

    assert len(rows) == 1


async def test_a_student_is_not_put_on_a_course() -> None:
    """
    The mistyped address is the whole reason this refusal exists.

    A student on the reviewers' table reads the work of everybody in their own group.
    """
    student = make_user(email="student@example.org")
    service, course, assignments = _service(people=[student])

    with pytest.raises(NotStaffError):
        await service.add_reviewer(course_id=course.id, email="student@example.org")

    assert assignments.rows == []


async def test_an_unknown_address_is_refused_the_same_way() -> None:
    """Nobody signed in with it, so there is nobody to put on anything."""
    service, course, _ = _service()

    with pytest.raises(NotStaffError):
        await service.add_reviewer(course_id=course.id, email="nobody@example.org")


async def test_the_same_person_added_twice_stays_one_row() -> None:
    """Pressing the button twice is not a decision to add somebody twice."""
    teacher = make_user(email="teacher@example.org", role=UserRole.INSTRUCTOR)
    service, course, assignments = _service(people=[teacher])

    await service.add_reviewer(course_id=course.id, email="teacher@example.org")
    rows = await service.add_reviewer(course_id=course.id, email="teacher@example.org")

    assert len(rows) == 1
    assert len(assignments.rows) == 1


async def test_taking_somebody_off_leaves_the_course_without_them() -> None:
    """Removal is about future work, not about what was already checked."""
    teacher = make_user(email="teacher@example.org", role=UserRole.INSTRUCTOR)
    service, course, assignments = _service(people=[teacher])
    rows = await service.add_reviewer(course_id=course.id, email="teacher@example.org")

    left = await service.remove_reviewer(course_id=course.id, assignment_id=rows[0].id)

    assert left == []
    assert assignments.rows == []


async def test_a_row_of_another_course_is_not_removed_from_this_one() -> None:
    """The row id alone would let one course's screen edit another's."""
    teacher = make_user(email="teacher@example.org", role=UserRole.INSTRUCTOR)
    service, course, assignments = _service(people=[teacher])
    elsewhere = await assignments.add(course_id=uuid7(), user_id=teacher.id)

    with pytest.raises(ReviewerNotFoundError):
        await service.remove_reviewer(course_id=course.id, assignment_id=elsewhere.id)


async def test_an_unknown_course_says_nothing_about_what_exists() -> None:
    """Same refusal for a guessed id as for a course that is simply not there."""
    service, _, _ = _service()

    with pytest.raises(CourseNotFoundForReviewersError):
        await service.list_reviewers(uuid7())
