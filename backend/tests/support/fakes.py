"""
Hand-written stand-ins for repositories.

A MagicMock accepts any call and returns another mock, so a renamed repository method
leaves the test green while production breaks. These raise AttributeError instead.
"""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID

from models.accreditation import Accreditation
from models.base import uuid7
from models.course import Course
from models.course_benefit import CourseBenefit
from models.course_question import CourseQuestion
from models.course_unit import CourseUnit
from models.entitlement import Entitlement
from models.enums import (
    AccessSource,
    Audience,
    CourseStatus,
    CourseUnitKind,
    MediaStatus,
    UnitStatus,
    UserRole,
)
from models.lesson import Lesson
from models.lesson_progress import LessonProgress
from models.media_file import MediaFile
from models.quiz import Quiz
from models.quiz_attempt import QuizAttempt, QuizAttemptAnswer
from models.quiz_question import QuizOption, QuizQuestion
from models.refresh_token import RefreshToken
from models.review import Review
from models.specialization import Specialization
from models.user import User
from services.billing import AccessRequiredError


class FakeCourseRepo:
    """In-memory course storage that applies the same filters the SQL does."""

    def __init__(self, courses: Sequence[Course]) -> None:
        self.courses = list(courses)
        self.calls: list[dict[str, object]] = []

    async def list_published(
        self,
        *,
        specialization_slug: str | None,
        accreditation_slug: str | None,
        audience: Audience | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Course], int]:
        """Record the arguments and return the matching slice."""
        self.calls.append(
            {
                "specialization_slug": specialization_slug,
                "accreditation_slug": accreditation_slug,
                "audience": audience,
                "search": search,
                "limit": limit,
                "offset": offset,
            }
        )
        matched = [
            course
            for course in self.courses
            if (specialization_slug is None or course.specialization.slug == specialization_slug)
            and (
                accreditation_slug is None
                or (
                    course.accreditation is not None
                    and course.accreditation.slug == accreditation_slug
                )
            )
            and (audience is None or course.specialization.audience is audience)
            and (search is None or search.lower() in course.title.lower())
        ]
        return matched[offset : offset + limit], len(matched)

    async def get_published_by_slug(self, slug: str) -> Course | None:
        """Find one course by slug, the way the query does."""
        return next((course for course in self.courses if course.slug == slug), None)

    async def get_published_by_id(self, course_id: UUID) -> Course | None:
        """Find one course by id, the way the lesson pages do."""
        return next((course for course in self.courses if course.id == course_id), None)


class FakeAdminRepo:
    """In-memory storage for the administration, drafts included."""

    def __init__(
        self,
        courses: Sequence[Course] = (),
        units: Sequence[CourseUnit] = (),
        lessons: Sequence[Lesson] = (),
        students: Mapping[UUID, int] | None = None,
    ) -> None:
        self.courses = list(courses)
        self.units = list(units)
        self.lessons = list(lessons)
        self.students = dict(students or {})
        self.flushes = 0

    async def list_courses(
        self,
        *,
        status: CourseStatus | None = None,
        specialization_id: UUID | None = None,
        query: str = "",
    ) -> Sequence[Course]:
        """Courses the fake was built with, filtered the way the SQL filters them."""
        found = self.courses
        if status is not None:
            found = [course for course in found if course.status is status]
        if specialization_id is not None:
            found = [course for course in found if course.specialization_id == specialization_id]
        if query:
            found = [course for course in found if query.lower() in course.title.lower()]
        return found

    async def get_course(self, course_id: UUID) -> Course | None:
        """One course by id, whatever its status."""
        return next((course for course in self.courses if course.id == course_id), None)

    async def count_units(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """Modules per course."""
        return {
            course_id: len(
                [
                    unit
                    for unit in self.units
                    if unit.course_id == course_id and unit.kind is CourseUnitKind.MODULE
                ]
            )
            for course_id in course_ids
        }

    async def count_students(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """Students per course. The fake counts whatever it was handed."""
        return {course_id: self.students.get(course_id, 0) for course_id in course_ids}

    async def slug_taken(self, slug: str, *, except_id: UUID | None = None) -> bool:
        """Whether another course already lives at this address."""
        return any(course.slug == slug and course.id != except_id for course in self.courses)

    async def add_course(self, course: Course) -> Course:
        """Insert a course."""
        self.courses.append(course)
        return course

    async def delete_course(self, course: Course) -> None:
        """Erase a course."""
        self.courses.remove(course)

    async def count_lessons(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """Live lectures per course."""
        units = {unit.id: unit.course_id for unit in self.units}
        counts: dict[UUID, int] = dict.fromkeys(course_ids, 0)
        for lesson in self.lessons:
            course_id = units.get(lesson.unit_id)
            if course_id in counts and lesson.deleted_at is None:
                counts[course_id] += 1
        return counts

    async def set_status(self, course: Course, status: CourseStatus) -> None:
        """Publish or unpublish."""
        course.status = status

    async def add_unit(self, unit: CourseUnit) -> CourseUnit:
        """Insert a line of the programme."""
        unit.id = uuid7()
        self.units.append(unit)
        return unit

    async def next_position(self, *, course_id: UUID, kind: CourseUnitKind) -> int:
        """After the last line of the same kind."""
        positions = [
            unit.position
            for unit in self.units
            if unit.course_id == course_id and unit.kind is kind
        ]
        return max(positions, default=0) + 1

    async def siblings(self, unit: CourseUnit) -> Sequence[CourseUnit]:
        """Lines of the same course and kind, in order."""
        return sorted(
            (
                other
                for other in self.units
                if other.course_id == unit.course_id and other.kind is unit.kind
            ),
            key=lambda row: row.position,
        )

    async def delete_unit(self, unit: CourseUnit) -> None:
        """Remove a line."""
        self.units = [other for other in self.units if other.id != unit.id]

    async def add_lesson(self, lesson: Lesson) -> Lesson:
        """Insert a lecture."""
        lesson.id = uuid7()
        self.lessons.append(lesson)
        return lesson

    async def next_lesson_position(self, unit_id: UUID) -> int:
        """After the last lecture of the module."""
        positions = [lesson.position for lesson in self.lessons if lesson.unit_id == unit_id]
        return max(positions, default=0) + 1

    async def lesson_siblings(self, unit_id: UUID) -> Sequence[Lesson]:
        """Live lectures of one module, in order."""
        return sorted(
            (
                lesson
                for lesson in self.lessons
                if lesson.unit_id == unit_id and lesson.deleted_at is None
            ),
            key=lambda row: row.position,
        )

    async def soft_delete_lesson(self, lesson: Lesson) -> None:
        """Retire a lecture."""
        lesson.deleted_at = datetime.now(UTC)

    async def flush(self) -> None:
        """Count the flushes, so a test can see the reorder was pushed at once."""
        self.flushes += 1


class FakeBenefitRepo:
    """In-memory storage for the «why this course» blocks."""

    def __init__(self, benefits: Sequence[CourseBenefit] = ()) -> None:
        self.benefits = list(benefits)

    async def list_for_course(self, course_id: UUID) -> Sequence[CourseBenefit]:
        """Return every reason listed under one course."""
        return self.benefits


class FakeLessonRepo:
    """In-memory lesson storage plus one student's facts about the lessons."""

    def __init__(
        self, lessons: Sequence[Lesson] = (), statuses: dict[UUID, str] | None = None
    ) -> None:
        self.lessons = list(lessons)
        self.statuses = statuses or {}
        self.completed: list[tuple[UUID, UUID]] = []
        self.playback: dict[tuple[UUID, UUID], LessonProgress] = {}

    async def get(self, lesson_id: UUID) -> Lesson | None:
        """One lesson by id."""
        return next((lesson for lesson in self.lessons if lesson.id == lesson_id), None)

    async def list_for_unit(self, unit_id: UUID) -> Sequence[Lesson]:
        """Every lesson of one module."""
        return [lesson for lesson in self.lessons if lesson.unit_id == unit_id]

    async def list_for_course(self, course_id: UUID) -> Sequence[Lesson]:
        """Every lesson handed in; the fake holds one course at a time."""
        return list(self.lessons)

    async def statuses_for_course(self, *, user_id: UUID, course_id: UUID) -> dict[UUID, str]:
        """One student's lesson statuses."""
        return dict(self.statuses)

    async def mark_completed(self, *, user_id: UUID, lesson_id: UUID) -> None:
        """Record the mark, so a test can see it happened exactly once per call."""
        self.completed.append((user_id, lesson_id))

    async def get_progress(self, *, user_id: UUID, lesson_id: UUID) -> LessonProgress | None:
        """One student's row for one lesson."""
        return self.playback.get((user_id, lesson_id))

    async def record_playback(
        self, *, user_id: UUID, lesson_id: UUID, position_sec: int, watched_delta: int
    ) -> LessonProgress:
        """Accumulate played time the way the upsert does."""
        row = self.playback.get((user_id, lesson_id))
        if row is None:
            row = LessonProgress(
                id=uuid7(),
                user_id=user_id,
                lesson_id=lesson_id,
                status=UnitStatus.IN_PROGRESS,
                last_position_sec=position_sec,
                watched_seconds=watched_delta,
            )
            self.playback[(user_id, lesson_id)] = row
            return row
        row.last_position_sec = position_sec
        row.watched_seconds += watched_delta
        return row


class FakeSyllabusRepo:
    """In-memory outline storage plus one student's facts about it."""

    def __init__(
        self, units: Sequence[CourseUnit], statuses: dict[UUID, str] | None = None
    ) -> None:
        self.units = list(units)
        self.statuses = statuses or {}
        self.asked_for: list[UUID] = []

    async def list_units(self, course_id: UUID) -> Sequence[CourseUnit]:
        """Return the outline of one course."""
        return [unit for unit in self.units if unit.course_id == course_id]

    async def statuses_for(self, *, user_id: UUID, course_id: UUID) -> dict[UUID, str]:
        """Return one student's statuses, recording that they were asked for at all."""
        self.asked_for.append(user_id)
        return dict(self.statuses)

    async def get_unit(self, unit_id: UUID) -> CourseUnit | None:
        """One line of the outline by id."""
        return next((unit for unit in self.units if unit.id == unit_id), None)

    async def mark_unit(self, *, user_id: UUID, unit_id: UUID, status: UnitStatus) -> None:
        """Record how far a student got in one unit."""
        self.statuses[unit_id] = str(status)


class FakeReviewRepo:
    """In-memory review storage that pages the same way the query does."""

    def __init__(self, reviews: Sequence[Review]) -> None:
        self.reviews = list(reviews)

    async def page(
        self, *, course_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Review], int]:
        """Return one page of reviews and the total."""
        return self.reviews[offset : offset + limit], len(self.reviews)

    async def counts_by_rating(self, course_id: UUID) -> dict[int, int]:
        """Group the reviews by rating."""
        counts: dict[int, int] = {}
        for review in self.reviews:
            counts[review.rating] = counts.get(review.rating, 0) + 1
        return counts


class FakeQuestionRepo:
    """In-memory storage for the discussion block."""

    def __init__(self, questions: Sequence[CourseQuestion]) -> None:
        self.questions = list(questions)

    async def list_for_course(self, course_id: UUID) -> Sequence[CourseQuestion]:
        """Return every question of one course."""
        return self.questions


class FakeSpecializationRepo:
    """In-memory specialization storage."""

    def __init__(self, items: Sequence[Specialization]) -> None:
        self.items = list(items)

    async def list_active(self) -> Sequence[Specialization]:
        """Return every specialization."""
        return self.items


class FakeAccreditationRepo:
    """In-memory accreditation storage."""

    def __init__(self, items: Sequence[Accreditation]) -> None:
        self.items = list(items)

    async def list_active(self) -> Sequence[Accreditation]:
        """Return every accreditation scheme."""
        return self.items


class FakeQuizRepo:
    """
    In-memory quiz storage.

    Options hang off the questions here, the way the fake's callers build them; the real
    repository fetches them in a second query. Both answer the same two methods, which is
    what the service is written against.
    """

    def __init__(self, quiz: Quiz, questions: Sequence[QuizQuestion]) -> None:
        self.quiz = quiz
        self.questions = list(questions)
        self.attempts: list[QuizAttempt] = []
        self.answers: list[QuizAttemptAnswer] = []

    async def get_by_unit(self, unit_id: UUID) -> Quiz | None:
        """The test of this unit, if it is the one the fake was built with."""
        return self.quiz if self.quiz.unit_id == unit_id else None

    async def list_questions(self, quiz_id: UUID) -> Sequence[QuizQuestion]:
        """Live questions of the test."""
        return [question for question in self.questions if question.deleted_at is None]

    async def list_options(self, question_ids: Sequence[UUID]) -> Sequence[QuizOption]:
        """Options of the given questions."""
        wanted = set(question_ids)
        return [
            option
            for question in self.questions
            if question.id in wanted
            for option in getattr(question, "options", [])
        ]

    async def latest_attempt(self, *, user_id: UUID, quiz_id: UUID) -> QuizAttempt | None:
        """The student's most recent attempt."""
        mine = [attempt for attempt in self.attempts if attempt.user_id == user_id]
        return mine[-1] if mine else None

    async def count_attempts(self, *, user_id: UUID, quiz_id: UUID) -> int:
        """How many attempts the student has spent."""
        return len([attempt for attempt in self.attempts if attempt.user_id == user_id])

    async def add_attempt(self, attempt: QuizAttempt, answers: Sequence[QuizAttemptAnswer]) -> None:
        """Store a graded attempt with its answers."""
        attempt.id = uuid7()
        self.attempts.append(attempt)
        self.answers.extend(answers)


class FakeUserRepo:
    """In-memory account storage."""

    def __init__(self, users: Sequence[User] = ()) -> None:
        self.users = list(users)

    async def get_by_email(self, email: str) -> User | None:
        """Find an account by address, matching the lower-cased storage convention."""
        wanted = email.lower()
        return next((user for user in self.users if user.email == wanted), None)

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find an account by id."""
        return next((user for user in self.users if user.id == user_id), None)

    async def update_full_name(self, user: User, *, full_name: str) -> User:
        """Store a new display name."""
        user.full_name = full_name
        return user

    async def set_password(self, user: User, *, password_hash: str) -> User:
        """Store a new password hash."""
        user.password_hash = password_hash
        return user

    async def create(
        self, *, email: str, password_hash: str, full_name: str, role: UserRole
    ) -> User:
        """Insert an account with an id already assigned."""
        user = User(
            id=uuid7(),
            email=email.lower(),
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        self.users.append(user)
        return user


class FakeRefreshTokenRepo:
    """In-memory refresh-token storage that keeps the same revocation semantics as SQL."""

    def __init__(self, tokens: Sequence[RefreshToken] = ()) -> None:
        self.tokens = list(tokens)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Find an issued token by its stored hash."""
        return next((token for token in self.tokens if token.token_hash == token_hash), None)

    async def create(
        self, *, user_id: UUID, token_hash: str, family_id: UUID, expires_at: datetime
    ) -> RefreshToken:
        """Store a newly issued token."""
        token = RefreshToken(
            id=uuid7(),
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        self.tokens.append(token)
        return token

    async def revoke(self, token: RefreshToken, *, at: datetime) -> None:
        """Mark one token as spent."""
        token.revoked_at = at

    async def revoke_all_for_user(self, user_id: UUID, *, at: datetime) -> int:
        """Revoke every live token of one account."""
        revoked = [
            token for token in self.tokens if token.user_id == user_id and token.revoked_at is None
        ]
        for token in revoked:
            token.revoked_at = at
        return len(revoked)

    async def revoke_family(self, family_id: UUID, *, at: datetime) -> None:
        """Revoke every live token of one login chain."""
        for token in self.tokens:
            if token.family_id == family_id and token.revoked_at is None:
                token.revoked_at = at

    @property
    def live(self) -> list[RefreshToken]:
        """Tokens that have not been revoked, which is what a session actually depends on."""
        return [token for token in self.tokens if token.revoked_at is None]


class FakeCounterStore:
    """In-memory fixed-window counters, with a switch to simulate the store being down."""

    def __init__(self, *, broken: bool = False) -> None:
        self.counts: dict[str, int] = {}
        self.broken = broken

    async def increment(self, key: str, *, window_seconds: int) -> tuple[int, int]:
        """Count one hit and report the running total with the seconds left."""
        if self.broken:
            raise ConnectionError("counter store is down")
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key], window_seconds


class FakeMediaRepo:
    """In-memory storage for uploaded files."""

    def __init__(self, files: Sequence[MediaFile] = ()) -> None:
        self.files = list(files)

    async def get(self, media_id: UUID) -> MediaFile | None:
        """One media row."""
        return next((media for media in self.files if media.id == media_id), None)

    async def create(
        self,
        *,
        bucket: str,
        key: str,
        is_public: bool,
        original_name: str,
        content_type: str,
        size_bytes: int,
        uploaded_by_id: UUID | None,
    ) -> MediaFile:
        """Write down an upload about to start."""
        media = MediaFile(
            id=uuid7(),
            bucket=bucket,
            key=key,
            is_public=is_public,
            original_name=original_name,
            content_type=content_type,
            size_bytes=size_bytes,
            status=MediaStatus.PENDING,
            uploaded_by_id=uploaded_by_id,
        )
        self.files.append(media)
        return media

    async def mark_ready(
        self, media: MediaFile, *, size_bytes: int, duration_seconds: int
    ) -> MediaFile:
        """Record that the object arrived."""
        media.size_bytes = size_bytes
        media.duration_seconds = duration_seconds
        media.status = MediaStatus.READY
        return media


class FakeEnrollmentRepo:
    """In-memory study records."""

    def __init__(self) -> None:
        self.records: dict[tuple[UUID, UUID], UUID | None] = {}

    async def ensure(self, *, user_id: UUID, course_id: UUID, last_lesson_id: UUID | None) -> None:
        """Enrol, or move the «continue» marker of an existing record."""
        self.records[(user_id, course_id)] = last_lesson_id


class FakeBilling:
    """
    A billing service that says yes or no, and remembers what it was asked.

    Handwritten rather than a mock: what matters in a test is that the question was asked
    at all, and a mock that answers every call the same way cannot tell that apart from a
    route that never asked.
    """

    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed
        self.asked: list[UUID] = []

    async def has_access(self, *, user: User | None, course_id: UUID) -> bool:
        """The prepared answer, and a note that the question was put."""
        self.asked.append(course_id)
        return self.allowed and user is not None

    async def require_access(self, *, user: User | None, course_id: UUID) -> None:
        """The same, refusing instead of answering False."""
        if not await self.has_access(user=user, course_id=course_id):
            raise AccessRequiredError(course_id)


class FakeEntitlementRepo:
    """In-memory rights of access."""

    def __init__(self, entitlements: Sequence[Entitlement] = ()) -> None:
        self.entitlements = list(entitlements)

    async def has_live(self, *, user_id: UUID, course_id: UUID, at: datetime) -> bool:
        """Whether an unrevoked, unexpired right covers this course."""
        return any(
            entitlement.user_id == user_id
            and entitlement.course_id in (course_id, None)
            and entitlement.revoked_at is None
            and entitlement.starts_at <= at
            and (entitlement.ends_at is None or entitlement.ends_at > at)
            for entitlement in self.entitlements
        )

    async def get(self, entitlement_id: UUID) -> Entitlement | None:
        """One grant by its id."""
        return next((item for item in self.entitlements if item.id == entitlement_id), None)

    async def create(
        self,
        *,
        user_id: UUID,
        course_id: UUID | None,
        source: AccessSource,
        granted_by_id: UUID | None,
        reason: str,
        ends_at: datetime | None,
    ) -> Entitlement:
        """Grant a right."""
        entitlement = Entitlement(
            id=uuid7(),
            user_id=user_id,
            course_id=course_id,
            source=source,
            starts_at=datetime.now(UTC),
            ends_at=ends_at,
            granted_by_id=granted_by_id,
            reason=reason,
        )
        self.entitlements.append(entitlement)
        return entitlement

    async def revoke(self, entitlement: Entitlement, *, at: datetime) -> Entitlement:
        """Withdraw a right, keeping the row."""
        entitlement.revoked_at = at
        return entitlement


class FakeCompletion:
    """
    The neighbour that decides whether a course has just been finished.

    Handwritten so a test can assert the question was asked at all: a service that quietly
    stops asking it leaves students with courses that never close.
    """

    def __init__(self) -> None:
        self.asked: list[UUID] = []

    async def note_progress(self, *, viewer: User, course_id: UUID) -> bool:
        """Remember the question; nothing here finishes a course."""
        self.asked.append(course_id)
        return False
