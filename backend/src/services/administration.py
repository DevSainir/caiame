from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from core.text import slugify
from models.course import Course
from models.course_unit import CourseUnit
from models.enums import CourseStatus, CourseUnitKind, MediaStatus
from models.lesson import Lesson
from models.media_file import MediaFile
from schemas.admin import (
    CourseDetailOut,
    CourseIn,
    CourseRowOut,
    CourseTreeOut,
    LessonDetailOut,
    LessonIn,
    LessonRowOut,
    MaterialOut,
    UnitIn,
    UnitRowOut,
    UnitUpdateIn,
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

    async def list_courses(self) -> Sequence[Course]: ...
    async def get_course(self, course_id: UUID) -> Course | None: ...
    async def count_units(self, course_ids: Sequence[UUID]) -> dict[UUID, int]: ...
    async def count_lessons(self, course_ids: Sequence[UUID]) -> dict[UUID, int]: ...
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

    async def list_courses(self) -> list[CourseRowOut]:
        """Every course of the academy with the size of its programme."""
        courses = await self.admin_repo.list_courses()
        ids = [course.id for course in courses]
        modules = await self.admin_repo.count_units(ids)
        lessons = await self.admin_repo.count_lessons(ids)
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
            )
            for course in courses
        ]

    async def get_tree(self, course_id: UUID) -> CourseTreeOut:
        """The programme of one course: modules with their lectures, then the works."""
        course = await self._course(course_id)
        units = await self.unit_repo.list_units(course.id)
        lessons = await self.lesson_repo.list_for_course(course.id)
        by_unit: dict[UUID, list[Lesson]] = {}
        for lesson in lessons:
            by_unit.setdefault(lesson.unit_id, []).append(lesson)

        rows = [self._unit_row(unit, by_unit.get(unit.id, [])) for unit in units]
        return CourseTreeOut(
            id=course.id,
            slug=course.slug,
            title=course.title,
            status=course.status,
            modules=[row for row in rows if row.kind is CourseUnitKind.MODULE],
            activities=[row for row in rows if row.kind is not CourseUnitKind.MODULE],
        )

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

    async def get_lesson_detail(self, *, course_id: UUID, lesson_id: UUID) -> LessonDetailOut:
        """One lecture with the file behind it, as its editing screen shows it."""
        lesson = await self._lesson(course_id, lesson_id)
        return LessonDetailOut(
            id=lesson.id,
            unit_id=lesson.unit_id,
            position=lesson.position,
            title=lesson.title,
            description=lesson.description,
            kind=lesson.kind,
            duration_minutes=lesson.duration_minutes,
            is_required=lesson.is_required,
            material=await self._material(lesson),
        )

    async def attach_material(
        self, *, course_id: UUID, lesson_id: UUID, media_id: UUID
    ) -> LessonDetailOut:
        """
        Point a lecture at a file that has finished uploading.

        Only a confirmed file may be attached: a lecture pointing at an upload that broke
        halfway shows a player that fails, which is worse than a lecture that honestly has
        no material yet.
        """
        lesson = await self._lesson(course_id, lesson_id)
        media = await self.media_repo.get(media_id)
        if media is None or media.status is not MediaStatus.READY:
            raise MaterialNotReadyError(media_id)
        lesson.media_file_id = media.id
        await self.admin_repo.flush()
        return await self.get_lesson_detail(course_id=course_id, lesson_id=lesson_id)

    async def _free_slug(self, base: str) -> str:
        """The address for a new course: the transliterated title, or the next free number."""
        if not await self.admin_repo.slug_taken(base):
            return base
        for suffix in range(2, 100):
            candidate = f"{base}-{suffix}"
            if not await self.admin_repo.slug_taken(candidate):
                return candidate
        raise SlugTakenError(base)

    async def _material(self, lesson: Lesson) -> MaterialOut | None:
        """The file behind a lecture, if there is one and it really arrived."""
        if lesson.media_file_id is None:
            return None
        media = await self.media_repo.get(lesson.media_file_id)
        if media is None or media.status is not MediaStatus.READY:
            return None
        return MaterialOut(
            id=media.id,
            original_name=media.original_name,
            size_bytes=media.size_bytes,
            duration_seconds=media.duration_seconds,
            content_type=media.content_type,
            uploaded_at=media.updated_at,
        )

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

    async def set_status(self, *, course_id: UUID, status: CourseStatus) -> CourseTreeOut:
        """Publish a course or take it out of the catalogue."""
        course = await self._course(course_id)
        await self.admin_repo.set_status(course, status)
        return await self.get_tree(course_id)

    async def add_unit(self, *, course_id: UUID, payload: UnitIn) -> UnitRowOut:
        """Add a module, an assignment or a test to the end of its own kind."""
        course = await self._course(course_id)
        position = await self.admin_repo.next_position(course_id=course.id, kind=payload.kind)
        unit = await self.admin_repo.add_unit(
            CourseUnit(
                course_id=course.id,
                kind=payload.kind,
                position=position,
                title=payload.title,
                summary=payload.summary,
            )
        )
        return self._unit_row(unit, [])

    async def update_unit(
        self, *, course_id: UUID, unit_id: UUID, payload: UnitUpdateIn
    ) -> UnitRowOut:
        """Rename a line of the programme. Its kind never changes — that would be a new line."""
        unit = await self._unit(course_id, unit_id)
        unit.title = payload.title
        unit.summary = payload.summary
        lessons = await self.admin_repo.lesson_siblings(unit.id)
        return self._unit_row(unit, list(lessons))

    async def move_unit(self, *, course_id: UUID, unit_id: UUID, direction: int) -> None:
        """
        Move a line one step within its own kind.

        A swap of two positions in one transaction, not a rewrite of the whole order:
        a partial reorder leaves two rows on the same position, and the list starts
        changing its shape between requests.
        """
        unit = await self._unit(course_id, unit_id)
        siblings = list(await self.admin_repo.siblings(unit))
        _swap(siblings, unit.id, direction)
        await self.admin_repo.flush()

    async def delete_unit(self, *, course_id: UUID, unit_id: UUID) -> None:
        """Remove an empty line of the programme; a module with lectures is refused."""
        unit = await self._unit(course_id, unit_id)
        if unit.kind is CourseUnitKind.MODULE:
            lessons = await self.admin_repo.lesson_siblings(unit.id)
            if lessons:
                raise ModuleNotEmptyError(unit_id)
        await self.admin_repo.delete_unit(unit)

    async def add_lesson(
        self, *, course_id: UUID, unit_id: UUID, payload: LessonIn
    ) -> LessonRowOut:
        """Add a lecture to the end of a module."""
        unit = await self._unit(course_id, unit_id)
        if unit.kind is not CourseUnitKind.MODULE:
            raise UnitNotFoundError(unit_id)
        position = await self.admin_repo.next_lesson_position(unit.id)
        lesson = await self.admin_repo.add_lesson(
            Lesson(
                unit_id=unit.id,
                position=position,
                title=payload.title,
                description=payload.description,
                kind=payload.kind,
                duration_minutes=payload.duration_minutes,
                is_required=payload.is_required,
            )
        )
        return _lesson_row(lesson)

    async def update_lesson(
        self, *, course_id: UUID, lesson_id: UUID, payload: LessonIn
    ) -> LessonRowOut:
        """Change a lecture. Replacing the material is a separate step."""
        lesson = await self._lesson(course_id, lesson_id)
        lesson.title = payload.title
        lesson.description = payload.description
        lesson.kind = payload.kind
        lesson.duration_minutes = payload.duration_minutes
        lesson.is_required = payload.is_required
        return _lesson_row(lesson)

    async def move_lesson(self, *, course_id: UUID, lesson_id: UUID, direction: int) -> None:
        """Move a lecture one step inside its module."""
        lesson = await self._lesson(course_id, lesson_id)
        siblings = list(await self.admin_repo.lesson_siblings(lesson.unit_id))
        _swap(siblings, lesson.id, direction)
        await self.admin_repo.flush()

    async def delete_lesson(self, *, course_id: UUID, lesson_id: UUID) -> None:
        """
        Retire a lecture.

        Soft: a student who finished eight of ten lectures must see 100 % after two
        unfinished ones are removed — the lecture leaves the denominator, not the history.
        """
        lesson = await self._lesson(course_id, lesson_id)
        await self.admin_repo.soft_delete_lesson(lesson)

    async def _course(self, course_id: UUID) -> Course:
        """The course, or a refusal that says nothing about what exists."""
        course = await self.admin_repo.get_course(course_id)
        if course is None:
            raise CourseNotFoundForAdminError(course_id)
        return course

    async def _unit(self, course_id: UUID, unit_id: UUID) -> CourseUnit:
        """A line of the programme that belongs to this very course."""
        unit = await self.unit_repo.get_unit(unit_id)
        if unit is None or unit.course_id != course_id:
            raise UnitNotFoundError(unit_id)
        return unit

    async def _lesson(self, course_id: UUID, lesson_id: UUID) -> Lesson:
        """A lecture that belongs to a module of this very course."""
        lesson = await self.lesson_repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFoundError(lesson_id)
        unit = await self.unit_repo.get_unit(lesson.unit_id)
        if unit is None or unit.course_id != course_id:
            raise LessonNotFoundError(lesson_id)
        return lesson

    def _unit_row(self, unit: CourseUnit, lessons: Sequence[Lesson]) -> UnitRowOut:
        """One line of the programme with the lectures under it."""
        return UnitRowOut(
            id=unit.id,
            kind=unit.kind,
            position=unit.position,
            title=unit.title,
            summary=unit.summary,
            lessons=[_lesson_row(lesson) for lesson in lessons],
        )


def _lesson_row(lesson: Lesson) -> LessonRowOut:
    """One lecture as the editor lists it."""
    return LessonRowOut(
        id=lesson.id,
        position=lesson.position,
        title=lesson.title,
        kind=lesson.kind,
        duration_minutes=lesson.duration_minutes,
        is_required=lesson.is_required,
        has_material=lesson.media_file_id is not None,
    )


def _swap(rows: Sequence[Positioned], row_id: UUID, direction: int) -> None:
    """
    Exchange the positions of a row and its neighbour.

    Both rows are written in the same transaction, so no request ever observes two rows
    claiming one position. A move past either end does nothing rather than failing: the
    button at the top of a list is not an error.
    """
    index = next((i for i, row in enumerate(rows) if row.id == row_id), None)
    if index is None:
        return
    target = index + (1 if direction > 0 else -1)
    if target < 0 or target >= len(rows):
        return
    rows[index].position, rows[target].position = rows[target].position, rows[index].position
