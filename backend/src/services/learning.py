from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, LessonKind, MediaStatus, UnitStatus
from models.lesson import Lesson
from models.lesson_progress import LessonProgress
from models.media_file import MediaFile
from models.user import User
from schemas.learning import (
    CourseRefOut,
    LessonDetailOut,
    LessonRowOut,
    LessonStatusOut,
    ModuleDetailOut,
    ModuleRefOut,
    PlaybackOut,
)


class LessonNotFoundError(Exception):
    """No such lesson, or it is not a lesson this student may open."""


class ModuleNotFoundError(Exception):
    """No such module in any published course."""


class CourseByIdReader(Protocol):
    """What the lesson pages need from the course storage."""

    async def get_published_by_id(self, course_id: UUID) -> Course | None:
        """Return one published course by its id, or nothing."""
        ...


class UnitReader(Protocol):
    """What the lesson pages need from the outline storage."""

    async def get_unit(self, unit_id: UUID) -> CourseUnit | None:
        """One line of the outline by its id."""
        ...


class AccessGuard(Protocol):
    """The one question about payment this service is allowed to ask."""

    async def has_access(self, *, user: User | None, course_id: UUID) -> bool:
        """Whether this account may open the material of this course."""
        ...

    async def require_access(self, *, user: User | None, course_id: UUID) -> None:
        """The same question, raising when the answer is no."""
        ...


class MaterialReader(Protocol):
    """What the lecture page needs to hand out a file."""

    async def get(self, media_id: UUID) -> MediaFile | None:
        """One media row."""
        ...


class MaterialSigner(Protocol):
    """Turning a stored object into a link that plays and then expires."""

    def playback_url(self, media: MediaFile) -> str:
        """A short-lived link to one object."""
        ...


class EnrolmentWriter(Protocol):
    """Where the fact «this student is taking this course» is recorded."""

    async def ensure(self, *, user_id: UUID, course_id: UUID, last_lesson_id: UUID | None) -> None:
        """Enrol a student if they are not enrolled, and remember where they were."""
        ...


class PlaybackWriter(Protocol):
    """Where played time is recorded."""

    async def record_playback(
        self, *, user_id: UUID, lesson_id: UUID, position_sec: int, watched_delta: int
    ) -> LessonProgress:
        """Add played seconds, remember the position, and hand back the row."""
        ...

    async def get_progress(self, *, user_id: UUID, lesson_id: UUID) -> LessonProgress | None:
        """One student's row for one lesson."""
        ...


class LessonReader(Protocol):
    """What the lesson pages need from the lesson storage."""

    async def get(self, lesson_id: UUID) -> Lesson | None:
        """One live lesson."""
        ...

    async def list_for_unit(self, unit_id: UUID) -> Sequence[Lesson]:
        """Every lesson of one module, in study order."""
        ...

    async def statuses_for_course(self, *, user_id: UUID, course_id: UUID) -> dict[UUID, str]:
        """One student's status per lesson of one course."""
        ...

    async def mark_completed(self, *, user_id: UUID, lesson_id: UUID) -> None:
        """Record that a student finished a lesson."""
        ...


# Titles and goodbyes at the end are not watched by everybody, and demanding the whole
# length turns into a stream of «I finished it and it did not count».
WATCHED_SHARE_TO_FINISH = 0.9
# A player reports every fifteen to thirty seconds; the ceiling is double that, so a slow
# tab still counts everything it played and a client inventing hours counts a minute.
MAX_REPORTED_SECONDS = 60


def completion_is_the_students_to_declare(kind: LessonKind) -> bool:
    """
    Whether pressing «finished» is what closes a lesson of this kind.

    The rule per kind lives here and in no `if` anywhere else. A handout is closed by the
    student saying so — nothing else can be observed about reading a file. A video is
    closed by how much of it was actually played, so the button is not what decides.
    """
    return kind is LessonKind.PDF


def is_watched_enough(*, watched_seconds: int, duration_seconds: int) -> bool:
    """
    Whether a video counts as watched.

    Measured against played time, never against the position: the position jumps wherever
    the slider is dragged, and a lecture that finishes on a drag to the end is a lecture
    nobody watched. A file of unknown length cannot be judged this way at all, and the
    honest answer there is «not yet».
    """
    if duration_seconds <= 0:
        return False
    return watched_seconds >= duration_seconds * WATCHED_SHARE_TO_FINISH


class LearningService:
    """The module page, the lecture page and the mark that closes a lecture."""

    def __init__(
        self,
        *,
        course_repo: CourseByIdReader,
        unit_repo: UnitReader,
        lesson_repo: LessonReader,
        media_repo: MaterialReader,
        playback_repo: PlaybackWriter,
        media_service: MaterialSigner,
        enrollment_repo: EnrolmentWriter,
        billing: AccessGuard,
    ) -> None:
        self.course_repo = course_repo
        self.unit_repo = unit_repo
        self.lesson_repo = lesson_repo
        self.media_repo = media_repo
        self.playback_repo = playback_repo
        self.media_service = media_service
        self.enrollment_repo = enrollment_repo
        self.billing = billing

    async def get_module(self, *, unit_id: UUID, viewer: User | None) -> ModuleDetailOut:
        """
        One module with its lectures and the asking student's progress in them.

        Open to anybody, including a visitor without an account: the list of lectures is
        part of what a course is selling. Opening a lecture is a different question, and it
        is answered in `get_lesson`; this page only says which way that answer will go.
        """
        unit = await self.unit_repo.get_unit(unit_id)
        if unit is None or unit.kind is not CourseUnitKind.MODULE:
            raise ModuleNotFoundError(unit_id)
        course = await self.course_repo.get_published_by_id(unit.course_id)
        if course is None:
            raise ModuleNotFoundError(unit_id)

        lessons = await self.lesson_repo.list_for_unit(unit.id)
        user_id = viewer.id if viewer else None
        statuses = await self._statuses(user_id=user_id, course_id=course.id)
        return ModuleDetailOut(
            id=unit.id,
            title=unit.title,
            summary=unit.summary,
            description=unit.summary,
            has_access=await self.billing.has_access(user=viewer, course_id=course.id),
            course=CourseRefOut.model_validate(course),
            lessons=[
                LessonRowOut(
                    id=lesson.id,
                    position=lesson.position,
                    title=lesson.title,
                    kind=lesson.kind,
                    duration_minutes=lesson.duration_minutes,
                    status=status_of(lesson.id, statuses),
                )
                for lesson in lessons
            ],
        )

    async def get_lesson(self, *, lesson_id: UUID, viewer: User) -> LessonDetailOut:
        """
        One lecture with the context the page shows above it.

        The right to open it is checked here, on every request, and not once when the course
        was entered: access ends between two page loads, and a check made at the door leaves
        the whole course open behind it. The link to the file is signed only after that
        check passes — the storage knows nothing about who paid.
        """
        lesson = await self.lesson_repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFoundError(lesson_id)
        unit = await self.unit_repo.get_unit(lesson.unit_id)
        if unit is None:
            raise LessonNotFoundError(lesson_id)
        course = await self.course_repo.get_published_by_id(unit.course_id)
        if course is None:
            raise LessonNotFoundError(lesson_id)

        await self.billing.require_access(user=viewer, course_id=course.id)
        # Enrolling happens at the first lecture a student is entitled to open, and the
        # record then follows them: it is what the «continue» button reads.
        await self.enrollment_repo.ensure(
            user_id=viewer.id, course_id=course.id, last_lesson_id=lesson.id
        )

        statuses = await self._statuses(user_id=viewer.id, course_id=course.id)
        progress = await self.playback_repo.get_progress(user_id=viewer.id, lesson_id=lesson.id)
        return LessonDetailOut(
            id=lesson.id,
            title=lesson.title,
            description=lesson.description,
            kind=lesson.kind,
            duration_minutes=lesson.duration_minutes,
            material_url=await self._material_url(lesson),
            status=status_of(lesson.id, statuses),
            last_position_sec=progress.last_position_sec if progress else 0,
            course=CourseRefOut.model_validate(course),
            module=ModuleRefOut(id=unit.id, title=unit.title),
        )

    async def report_playback(
        self, *, lesson_id: UUID, viewer: User, position_sec: int, delta_sec: int
    ) -> PlaybackOut:
        """
        Record that a stretch of a video was actually played.

        Two numbers arrive and they mean different things. The position is where the player
        is now — it moves anywhere, including backwards, and exists so the lecture reopens
        where it was left. The delta is time that really elapsed, and only it decides
        whether the lecture counts as watched.

        The delta is capped rather than believed. A client saying «I watched an hour» gets
        the ceiling for one report and no error: nothing about that is worth failing a
        request over, and nothing about it should count either.
        """
        lesson = await self.lesson_repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFoundError(lesson_id)
        unit = await self.unit_repo.get_unit(lesson.unit_id)
        if unit is None:
            raise LessonNotFoundError(lesson_id)
        await self.billing.require_access(user=viewer, course_id=unit.course_id)

        progress = await self.playback_repo.record_playback(
            user_id=viewer.id,
            lesson_id=lesson_id,
            position_sec=max(0, position_sec),
            watched_delta=min(max(0, delta_sec), MAX_REPORTED_SECONDS),
        )

        duration = await self._duration(lesson)
        if progress.status is not UnitStatus.DONE and is_watched_enough(
            watched_seconds=progress.watched_seconds, duration_seconds=duration
        ):
            await self.lesson_repo.mark_completed(user_id=viewer.id, lesson_id=lesson_id)
            return PlaybackOut(
                status=UnitStatus.DONE,
                watched_seconds=progress.watched_seconds,
                last_position_sec=progress.last_position_sec,
            )
        return PlaybackOut(
            status=progress.status,
            watched_seconds=progress.watched_seconds,
            last_position_sec=progress.last_position_sec,
        )

    async def _duration(self, lesson: Lesson) -> int:
        """
        How long the lecture actually is, in seconds.

        Read from the file, not from the minutes typed into the form: the form is a rounded
        hint for the listing, and rounding it down would finish a lecture early.
        """
        if lesson.media_file_id is None:
            return 0
        media = await self.media_repo.get(lesson.media_file_id)
        return media.duration_seconds if media is not None else 0

    async def complete_lesson(self, *, lesson_id: UUID, viewer: User) -> LessonStatusOut:
        """
        Mark a lecture finished for this student.

        Idempotent: the page sends it on every return and on every double click, and all of
        them are one event. A lesson that is already finished stays finished with the time
        it was first finished at.
        """
        lesson = await self.lesson_repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFoundError(lesson_id)
        unit = await self.unit_repo.get_unit(lesson.unit_id)
        if unit is None:
            raise LessonNotFoundError(lesson_id)
        # Asked again here: finishing a lecture is reading it, and a route that writes
        # progress for material the account may not open is the same hole with a nicer name.
        await self.billing.require_access(user=viewer, course_id=unit.course_id)
        await self.lesson_repo.mark_completed(user_id=viewer.id, lesson_id=lesson_id)
        return LessonStatusOut(status=UnitStatus.DONE)

    async def _material_url(self, lesson: Lesson) -> str | None:
        """
        A link to the file of this lecture, or nothing while it is still being prepared.

        A file that has not been confirmed in storage counts as absent: the page then says
        the material is not uploaded yet instead of showing a player that fails.
        """
        if lesson.media_file_id is None:
            return None
        media = await self.media_repo.get(lesson.media_file_id)
        if media is None or media.status is not MediaStatus.READY:
            return None
        return self.media_service.playback_url(media)

    async def _statuses(self, *, user_id: UUID | None, course_id: UUID) -> dict[UUID, str]:
        """One student's lesson statuses, or nothing at all for a visitor without a session."""
        if user_id is None:
            return {}
        return await self.lesson_repo.statuses_for_course(user_id=user_id, course_id=course_id)


def completion_percent(
    *, lessons_done: int, lessons_total: int, works_done: int, works_total: int
) -> int:
    """
    Share of a course that is finished.

    The rule itself, in one place: lectures and works are the atoms, modules are not counted
    again for containing lectures, a lecture in progress earns nothing, and optional
    lectures never reach the denominator. The course page and the administration list both
    call this — two implementations of one percentage disagree, and the disagreement is
    found by a student who is shown two different numbers for the same course.
    """
    total = lessons_total + works_total
    if total == 0:
        return 0
    return round((lessons_done + works_done) * 100 / total)


def status_of(lesson_id: UUID, statuses: dict[UUID, str]) -> UnitStatus:
    """The stored status of a lesson; anything unknown has not been started."""
    raw = statuses.get(lesson_id)
    return UnitStatus(raw) if raw is not None else UnitStatus.NOT_STARTED


def module_status(lessons: Sequence[Lesson], statuses: dict[UUID, str]) -> UnitStatus:
    """
    What a module's row on the course page shows.

    Derived from its lectures rather than stored: a module is a container, and a second
    place to write «done» is a second place to disagree with the lectures themselves.
    """
    if not lessons:
        return UnitStatus.NOT_STARTED
    marks = [status_of(lesson.id, statuses) for lesson in lessons]
    if all(mark is UnitStatus.DONE for mark in marks):
        return UnitStatus.DONE
    if any(mark is not UnitStatus.NOT_STARTED for mark in marks):
        return UnitStatus.IN_PROGRESS
    return UnitStatus.NOT_STARTED
