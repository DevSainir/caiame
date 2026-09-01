"""
«Мои курсы»: список того, что студент уже начал.

Both facts on that screen are counted at the moment of asking, and both are easy to get
wrong in a way nobody notices: a percentage that drifts from the lessons behind it, and a
course that disappears from the list the day access ends.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from models.base import uuid7
from models.course import Course
from models.enrollment import Enrollment
from models.user import User
from services.enrollment import EnrollmentService
from tests.support.factories import make_course, make_user


class FakeEnrollments:
    """Study records of one student."""

    def __init__(self, records: list[Enrollment]) -> None:
        self.records = records

    async def list_for_user(self, user_id: UUID) -> Sequence[Enrollment]:
        """Everything this student has started."""
        return [record for record in self.records if record.user_id == user_id]


class FakeCatalogue:
    """Courses by identifier, archived ones included."""

    def __init__(self, courses: list[Course]) -> None:
        self.courses = courses

    async def list_by_ids(self, course_ids: Sequence[UUID]) -> Sequence[Course]:
        """The courses asked for."""
        return [course for course in self.courses if course.id in set(course_ids)]


class FakeCounts:
    """The four numbers the percentage is made of."""

    def __init__(self, totals: dict[UUID, int], done: dict[tuple[UUID, UUID], int]) -> None:
        self.totals = totals
        self.done = done

    async def required_totals(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """Required lectures per course."""
        return self.totals

    async def done_by_student(
        self, *, course_ids: Sequence[UUID], user_ids: Sequence[UUID]
    ) -> dict[tuple[UUID, UUID], int]:
        """Finished lectures per student and course."""
        return self.done

    async def work_totals(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """Works per course."""
        return {}

    async def done_works_by_student(
        self, *, course_ids: Sequence[UUID], user_ids: Sequence[UUID]
    ) -> dict[tuple[UUID, UUID], int]:
        """Passed works per student and course."""
        return {}


class FakeBilling:
    """Access, prepared per course."""

    def __init__(self, *, allowed: bool) -> None:
        self.allowed = allowed

    async def has_access(self, *, user: User | None, course_id: UUID) -> bool:
        """The prepared answer."""
        return self.allowed


def _service(
    *, allowed: bool = True, done: int = 0, total: int = 4
) -> tuple[EnrollmentService, User, Course]:
    """A service over one student enrolled in one course."""
    student = make_user()
    course = make_course(slug="therapy")
    enrollment = Enrollment(
        id=uuid7(),
        user_id=student.id,
        course_id=course.id,
        started_at=datetime.now(UTC),
        last_lesson_id=None,
    )
    service = EnrollmentService(
        enrollment_repo=FakeEnrollments([enrollment]),
        course_repo=FakeCatalogue([course]),
        lesson_repo=FakeCounts({course.id: total}, {(student.id, course.id): done}),
        unit_repo=FakeCounts({}, {}),
        billing=FakeBilling(allowed=allowed),
    )
    return service, student, course


async def test_the_percentage_is_counted_from_the_lessons_behind_it() -> None:
    """Never stored: a stored number drifts away from the facts without saying so."""
    service, student, _ = _service(done=1, total=4)

    courses = await service.my_courses(viewer=student)

    assert courses[0].progress_percent == 25


async def test_a_course_stays_in_the_list_after_access_ends() -> None:
    """
    The study record outlives access, and so does everything under it.

    Dropping the course from the list would tell the student their studying is gone, which
    is exactly what the record is there to prevent.
    """
    service, student, _ = _service(allowed=False, done=2, total=4)

    courses = await service.my_courses(viewer=student)

    assert len(courses) == 1
    assert courses[0].has_access is False
    assert courses[0].progress_percent == 50


async def test_a_student_who_started_nothing_gets_an_empty_list() -> None:
    """Not an error and not a fabricated row: simply nothing yet."""
    service, _, _ = _service()

    assert await service.my_courses(viewer=make_user(email="nobody@example.org")) == []
