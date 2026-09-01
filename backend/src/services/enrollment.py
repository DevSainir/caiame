"""
«Мои курсы»: то, что студент уже начал.

Both numbers on this screen are computed at the moment of asking. The percentage is derived
from the facts about lessons and works, never stored — a stored one drifts away from them
silently. Access is asked per course, because a study record outlives access: the course
stays in the list, and its lectures stop opening.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.enrollment import Enrollment
from models.user import User
from schemas.enrollment import MyCourseOut
from services.learning import completion_percent


class EnrolmentStore(Protocol):
    """Study records of one student."""

    async def list_for_user(self, user_id: UUID) -> Sequence[Enrollment]: ...

    async def get(self, *, user_id: UUID, course_id: UUID) -> Enrollment | None: ...

    async def mark_completed(self, enrollment: Enrollment, *, at: datetime) -> Enrollment: ...


class CourseReader(Protocol):
    """Courses by identifier, whatever their status."""

    async def list_by_ids(self, course_ids: Sequence[UUID]) -> Sequence[Course]: ...


class LessonCounts(Protocol):
    """Required lectures per course, and how many of them this student finished."""

    async def required_totals(self, course_ids: Sequence[UUID]) -> dict[UUID, int]: ...

    async def done_by_student(
        self, *, course_ids: Sequence[UUID], user_ids: Sequence[UUID]
    ) -> dict[tuple[UUID, UUID], int]: ...


class WorkCounts(Protocol):
    """The same for assignments and tests."""

    async def work_totals(self, course_ids: Sequence[UUID]) -> dict[UUID, int]: ...

    async def done_works_by_student(
        self, *, course_ids: Sequence[UUID], user_ids: Sequence[UUID]
    ) -> dict[tuple[UUID, UUID], int]: ...


class AccessGuard(Protocol):
    """The one question about payment this service is allowed to ask."""

    async def has_access(self, *, user: User | None, course_id: UUID) -> bool: ...


class EnrollmentService:
    """The student's own list of courses."""

    def __init__(
        self,
        *,
        enrollment_repo: EnrolmentStore,
        course_repo: CourseReader,
        lesson_repo: LessonCounts,
        unit_repo: WorkCounts,
        billing: AccessGuard,
    ) -> None:
        self.enrollment_repo = enrollment_repo
        self.course_repo = course_repo
        self.lesson_repo = lesson_repo
        self.unit_repo = unit_repo
        self.billing = billing

    async def my_courses(self, *, viewer: User) -> list[MyCourseOut]:
        """
        Courses this student has started, most recent first.

        The counting is done in four queries for the whole list rather than four per course:
        a person with seven courses would otherwise pay twenty-eight round trips for one
        screen.
        """
        enrollments = await self.enrollment_repo.list_for_user(viewer.id)
        if not enrollments:
            return []

        course_ids = [enrollment.course_id for enrollment in enrollments]
        courses = {course.id: course for course in await self.course_repo.list_by_ids(course_ids)}
        lesson_totals = await self.lesson_repo.required_totals(course_ids)
        work_totals = await self.unit_repo.work_totals(course_ids)
        lessons_done = await self.lesson_repo.done_by_student(
            course_ids=course_ids, user_ids=[viewer.id]
        )
        works_done = await self.unit_repo.done_works_by_student(
            course_ids=course_ids, user_ids=[viewer.id]
        )

        rows: list[MyCourseOut] = []
        for enrollment in enrollments:
            course = courses.get(enrollment.course_id)
            if course is None:
                continue
            rows.append(
                MyCourseOut(
                    id=course.id,
                    slug=course.slug,
                    title=course.title,
                    cover_url=course.cover_url,
                    progress_percent=completion_percent(
                        lessons_done=lessons_done.get((viewer.id, course.id), 0),
                        lessons_total=lesson_totals.get(course.id, 0),
                        works_done=works_done.get((viewer.id, course.id), 0),
                        works_total=work_totals.get(course.id, 0),
                    ),
                    is_completed=enrollment.completed_at is not None,
                    has_access=await self.billing.has_access(user=viewer, course_id=course.id),
                    continue_lesson_id=enrollment.last_lesson_id,
                )
            )
        return rows

    async def note_progress(self, *, viewer: User, course_id: UUID) -> bool:
        """
        Check whether this student has just finished the course, and record it if so.

        Called after anything that can be the last thing left: a lecture marked read, a
        video watched to the end, a test passed, a piece of work accepted. Deliberately one
        place rather than a rule repeated in four services — the four would drift, and the
        drift would show up as a certificate that never arrives.

        Recording happens once. The percentage is derived and can fall afterwards — adding a
        lecture to a live course drops everybody's — but the course was finished, and that
        does not stop being true.
        """
        enrollment = await self.enrollment_repo.get(user_id=viewer.id, course_id=course_id)
        if enrollment is None or enrollment.completed_at is not None:
            return False
        if await self._percent(viewer=viewer, course_id=course_id) < 100:
            return False
        await self.enrollment_repo.mark_completed(enrollment, at=datetime.now(UTC))
        return True

    async def _percent(self, *, viewer: User, course_id: UUID) -> int:
        """How much of one course this student has finished, counted from the facts."""
        courses = [course_id]
        users = [viewer.id]
        return completion_percent(
            lessons_done=(
                await self.lesson_repo.done_by_student(course_ids=courses, user_ids=users)
            ).get((viewer.id, course_id), 0),
            lessons_total=(await self.lesson_repo.required_totals(courses)).get(course_id, 0),
            works_done=(
                await self.unit_repo.done_works_by_student(course_ids=courses, user_ids=users)
            ).get((viewer.id, course_id), 0),
            works_total=(await self.unit_repo.work_totals(courses)).get(course_id, 0),
        )
