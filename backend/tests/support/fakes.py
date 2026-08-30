"""
Hand-written stand-ins for repositories.

A MagicMock accepts any call and returns another mock, so a renamed repository method
leaves the test green while production breaks. These raise AttributeError instead.
"""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from models.accreditation import Accreditation
from models.base import uuid7
from models.course import Course
from models.course_benefit import CourseBenefit
from models.course_question import CourseQuestion
from models.course_unit import CourseUnit
from models.enums import Audience, UnitStatus, UserRole
from models.lesson import Lesson
from models.quiz import Quiz
from models.quiz_attempt import QuizAttempt, QuizAttemptAnswer
from models.quiz_question import QuizOption, QuizQuestion
from models.refresh_token import RefreshToken
from models.review import Review
from models.specialization import Specialization
from models.user import User


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
