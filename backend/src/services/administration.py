from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from core.text import slugify
from models.course import Course
from models.course_unit import CourseUnit
from models.enums import CourseStatus, CourseUnitKind
from models.lesson import Lesson
from models.media_file import MediaFile
from schemas.admin import (
    CourseDetailOut,
    CourseIn,
    CourseRowOut,
)


class CourseNotFoundForAdminError(Exception):
    """No such course, draft or published."""


class UnitNotFoundError(Exception):
    """No such line of the programme in this course."""


class LessonNotFoundError(Exception):
    """No such lecture in this module."""


class ModuleNotEmptyError(Exception):
    """A module still holds lectures, and removing it would take them with it."""


class CourseInUseError(Exception):
    """The course is published or has students, so erasing it would erase their studying."""


class SlugTakenError(Exception):
    """Another course already lives at this address."""


class MaterialNotReadyError(Exception):
    """The file has not arrived in storage, so it cannot be attached to a lecture."""


class Positioned(Protocol):
    """Anything the editor can reorder: it has an identity and a place in a list."""

    id: UUID
    position: int


class AdminStore(Protocol):
    """Everything the administration needs from storage."""

    async def list_courses(
        self,
        *,
        status: CourseStatus | None = None,
        specialization_id: UUID | None = None,
        query: str = "",
    ) -> Sequence[Course]: ...
    async def get_course(self, course_id: UUID) -> Course | None: ...
    async def count_units(self, course_ids: Sequence[UUID]) -> dict[UUID, int]: ...
    async def count_lessons(self, course_ids: Sequence[UUID]) -> dict[UUID, int]: ...
    async def count_lessons_without_material(
        self, course_ids: Sequence[UUID]
    ) -> dict[UUID, int]: ...
    async def count_students(self, course_ids: Sequence[UUID]) -> dict[UUID, int]: ...
    async def slug_taken(self, slug: str, *, except_id: UUID | None = None) -> bool: ...
    async def add_course(self, course: Course) -> Course: ...
    async def delete_course(self, course: Course) -> None: ...
    async def set_status(self, course: Course, status: CourseStatus) -> None: ...
    async def add_unit(self, unit: CourseUnit) -> CourseUnit: ...
    async def next_position(self, *, course_id: UUID, kind: CourseUnitKind) -> int: ...
    async def siblings(self, unit: CourseUnit) -> Sequence[CourseUnit]: ...
    async def delete_unit(self, unit: CourseUnit) -> None: ...
    async def add_lesson(self, lesson: Lesson) -> Lesson: ...
    async def next_lesson_position(self, unit_id: UUID) -> int: ...
    async def lesson_siblings(self, unit_id: UUID) -> Sequence[Lesson]: ...
    async def soft_delete_lesson(self, lesson: Lesson) -> None: ...
    async def flush(self) -> None: ...


class UnitStore(Protocol):
    """The outline, read the same way the student's page reads it."""

    async def get_unit(self, unit_id: UUID) -> CourseUnit | None: ...
    async def list_units(self, course_id: UUID) -> Sequence[CourseUnit]: ...


class LessonStore(Protocol):
    """Lectures, read the same way the module page reads them."""

    async def get(self, lesson_id: UUID) -> Lesson | None: ...
    async def list_for_course(self, course_id: UUID) -> Sequence[Lesson]: ...


class MediaStore(Protocol):
    """Uploaded files, as the editor needs to show and attach them."""

    async def get(self, media_id: UUID) -> MediaFile | None: ...


class AdministrationService:
    """
    What an administrator does to a course: build its programme and publish it.

    Every method starts from the course, not from the id in the address: a module that
    belongs to another course is «not found» here, so a guessed identifier cannot edit
    somebody else's programme.
    """

    def __init__(
        self,
        *,
        admin_repo: AdminStore,
        unit_repo: UnitStore,
        lesson_repo: LessonStore,
        media_repo: MediaStore,
    ) -> None:
        self.admin_repo = admin_repo
        self.unit_repo = unit_repo
        self.lesson_repo = lesson_repo
        self.media_repo = media_repo

    async def list_courses(
        self,
        *,
        status: CourseStatus | None = None,
        specialization_id: UUID | None = None,
        query: str = "",
    ) -> list[CourseRowOut]:
        """
        Courses of the academy with the size of the programme and how many are taking them.

        The student count is what tells a draft nobody has seen from a course that is being
        studied right now — and it is the reason the same course cannot simply be deleted.
        """
        courses = await self.admin_repo.list_courses(
            status=status, specialization_id=specialization_id, query=query
        )
        ids = [course.id for course in courses]
        modules = await self.admin_repo.count_units(ids)
        lessons = await self.admin_repo.count_lessons(ids)
        empty = await self.admin_repo.count_lessons_without_material(ids)
        students = await self.admin_repo.count_students(ids)
        return [
            CourseRowOut(
                id=course.id,
                slug=course.slug,
                title=course.title,
                status=course.status,
                credit_hours=course.credit_hours,
                specialization=course.specialization.name,
                modules=modules.get(course.id, 0),
                lessons=lessons.get(course.id, 0),
                lessons_without_material=empty.get(course.id, 0),
                students=students.get(course.id, 0),
            )
            for course in courses
        ]

    async def create_course(self, payload: CourseIn) -> CourseDetailOut:
        """
        Start a new course as a draft.

        A draft and not a published course, always: a course appears in the catalogue when
        somebody decides it is ready, never as a side effect of creating it. The address is
        made from the title once, here, and then belongs to the course — renaming the course
        later leaves it alone, because links to it are already in people's hands.
        """
        slug = await self._free_slug(slugify(payload.title, fallback="course"))
        course = await self.admin_repo.add_course(
            Course(
                slug=slug,
                title=payload.title,
                summary=payload.summary,
                description=payload.description,
                status=CourseStatus.DRAFT,
                specialization_id=payload.specialization_id,
                accreditation_id=payload.accreditation_id,
                credit_hours=payload.credit_hours,
                duration_hours=payload.duration_hours,
                price_minor=payload.price_minor,
            )
        )
        return self._course_detail(course, students=0)

    async def get_course_detail(self, course_id: UUID) -> CourseDetailOut:
        """One course as its own form shows it."""
        course = await self._course(course_id)
        students = await self.admin_repo.count_students([course.id])
        return self._course_detail(course, students=students.get(course.id, 0))

    async def update_course(self, *, course_id: UUID, payload: CourseIn) -> CourseDetailOut:
        """Change the description of a course. Its address stays where it is."""
        course = await self._course(course_id)
        course.title = payload.title
        course.summary = payload.summary
        course.description = payload.description
        course.specialization_id = payload.specialization_id
        course.accreditation_id = payload.accreditation_id
        course.credit_hours = payload.credit_hours
        course.duration_hours = payload.duration_hours
        course.price_minor = payload.price_minor
        await self.admin_repo.flush()
        students = await self.admin_repo.count_students([course.id])
        return self._course_detail(course, students=students.get(course.id, 0))

    async def delete_course(self, course_id: UUID) -> None:
        """
        Erase a draft nobody is taking.

        Anything else is refused. A course that has been published has been in front of
        people, and a course with students holds their progress under it; the way to retire
        those is to take them out of the catalogue, which keeps everything and shows nothing.
        """
        course = await self._course(course_id)
        students = await self.admin_repo.count_students([course.id])
        if course.status is not CourseStatus.DRAFT or students.get(course.id, 0) > 0:
            raise CourseInUseError(course_id)
        await self.admin_repo.delete_course(course)

    async def _free_slug(self, base: str) -> str:
        """The address for a new course: the transliterated title, or the next free number."""
        if not await self.admin_repo.slug_taken(base):
            return base
        for suffix in range(2, 100):
            candidate = f"{base}-{suffix}"
            if not await self.admin_repo.slug_taken(candidate):
                return candidate
        raise SlugTakenError(base)

    @staticmethod
    def _course_detail(course: Course, *, students: int) -> CourseDetailOut:
        """One course as the form reads it."""
        return CourseDetailOut(
            id=course.id,
            slug=course.slug,
            title=course.title,
            summary=course.summary,
            description=course.description,
            status=course.status,
            specialization_id=course.specialization_id,
            accreditation_id=course.accreditation_id,
            credit_hours=course.credit_hours,
            duration_hours=course.duration_hours,
            price_minor=course.price_minor,
            currency=course.currency,
            students=students,
        )

    async def set_status(self, *, course_id: UUID, status: CourseStatus) -> CourseDetailOut:
        """
        Publish a course or take it out of the catalogue.

        Answers with the course, not with its programme: the outline belongs to another
        service now, and the screen re-reads it anyway after any change.
        """
        course = await self._course(course_id)
        await self.admin_repo.set_status(course, status)
        students = await self.admin_repo.count_students([course.id])
        return self._course_detail(course, students=students.get(course.id, 0))

    async def _course(self, course_id: UUID) -> Course:
        """The course, or a refusal that says nothing about what exists."""
        course = await self.admin_repo.get_course(course_id)
        if course is None:
            raise CourseNotFoundForAdminError(course_id)
        return course
