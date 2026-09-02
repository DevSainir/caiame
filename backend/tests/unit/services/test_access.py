"""
The screen the academy opens courses from.

What is worth holding here is not the SQL but the shape of the answer: a right to the whole
catalogue is not a right to one course, a withdrawn right stays on the list rather than
disappearing from it, and the percentage against every row is the same percentage the
student sees on the course page — two numbers for one course is a conversation nobody wants.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import pytest

from models.base import uuid7
from models.course import Course
from models.entitlement import Entitlement
from models.enums import AccessSource
from models.user import User
from services.access import AccessService, GrantNotFoundError, StudentNotFoundError
from tests.support.factories import make_course, make_user


class FakeGrants:
    """The grants of one page, with the student and the course already attached."""

    def __init__(self, rows: Sequence[tuple[Entitlement, User, Course | None]]) -> None:
        self.rows = list(rows)

    async def list_grants(
        self, *, course_id: UUID | None, limit: int, offset: int
    ) -> Sequence[tuple[Entitlement, User, Course | None]]:
        """One page, newest first — the order is the repository's business."""
        return self.rows[offset : offset + limit]

    async def count_grants(self, *, course_id: UUID | None) -> int:
        """How many there are in total."""
        return len(self.rows)

    async def get(self, entitlement_id: UUID) -> Entitlement | None:
        """One grant by its id."""
        return next((row[0] for row in self.rows if row[0].id == entitlement_id), None)


class FakeGranting:
    """The billing service, remembering what it was asked to do."""

    def __init__(self) -> None:
        self.granted: list[tuple[UUID, UUID | None, str]] = []
        self.revoked: list[UUID] = []

    async def grant(
        self,
        *,
        user_id: UUID,
        course_id: UUID | None,
        granted_by_id: UUID,
        reason: str,
        source: AccessSource = AccessSource.MANUAL,
    ) -> Entitlement:
        """Write the right down."""
        self.granted.append((user_id, course_id, reason))
        return Entitlement(
            id=uuid7(),
            user_id=user_id,
            course_id=course_id,
            source=source,
            starts_at=datetime.now(UTC),
            granted_by_id=granted_by_id,
            reason=reason,
        )

    async def revoke(self, entitlement: Entitlement) -> Entitlement:
        """Withdraw it, keeping the row."""
        self.revoked.append(entitlement.id)
        entitlement.revoked_at = datetime.now(UTC)
        return entitlement


class FakePeople:
    """Accounts by address, as the form looks them up."""

    def __init__(self, people: Sequence[User]) -> None:
        self.people = list(people)

    async def get_by_email(self, email: str) -> User | None:
        """Whoever signed up with this address."""
        return next((person for person in self.people if person.email == email), None)


class FakeLessonCounts:
    """How many lectures a course requires, and how many each student finished."""

    def __init__(self, *, required: int = 0, done: int = 0) -> None:
        self.required = required
        self.done = done

    async def required_totals(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """The denominator, per course."""
        return dict.fromkeys(course_ids, self.required)

    async def done_by_student(
        self, *, course_ids: Sequence[UUID], user_ids: Sequence[UUID]
    ) -> dict[tuple[UUID, UUID], int]:
        """The numerator, per student and course."""
        return {(user, course): self.done for user in user_ids for course in course_ids}


class FakeWorkCounts:
    """The same for assignments and tests."""

    def __init__(self, *, total: int = 0, done: int = 0) -> None:
        self.total = total
        self.done = done

    async def work_totals(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        """How many works a course has."""
        return dict.fromkeys(course_ids, self.total)

    async def done_works_by_student(
        self, *, course_ids: Sequence[UUID], user_ids: Sequence[UUID]
    ) -> dict[tuple[UUID, UUID], int]:
        """How many of them each student closed."""
        return {(user, course): self.done for user in user_ids for course in course_ids}


def _grant(
    *, student: User, course: Course | None, revoked: bool = False, reason: str = "оплата в кассе"
) -> Entitlement:
    """One right, live or withdrawn."""
    return Entitlement(
        id=uuid7(),
        user_id=student.id,
        course_id=course.id if course else None,
        source=AccessSource.MANUAL,
        starts_at=datetime.now(UTC),
        revoked_at=datetime.now(UTC) if revoked else None,
        granted_by_id=uuid7(),
        reason=reason,
    )


def _service(
    rows: Sequence[tuple[Entitlement, User, Course | None]] = (),
    *,
    people: Sequence[User] = (),
    lessons: FakeLessonCounts | None = None,
    works: FakeWorkCounts | None = None,
) -> tuple[AccessService, FakeGranting, FakeGrants]:
    """The screen over the grants handed in."""
    grants = FakeGrants(rows)
    billing = FakeGranting()
    service = AccessService(
        entitlement_repo=grants,
        billing=billing,
        user_repo=FakePeople(people),
        lesson_repo=lessons or FakeLessonCounts(),
        unit_repo=works or FakeWorkCounts(),
    )
    return service, billing, grants


async def test_a_grant_is_written_for_the_account_behind_the_address() -> None:
    """The office has an address, not an identifier — and a reason, which is kept."""
    student = make_user(email="student@example.org")
    course = make_course(slug="therapy")
    service, billing, _ = _service(people=[student])

    await service.grant(
        email="student@example.org",
        course_id=course.id,
        granted_by_id=uuid7(),
        reason="оплата в кассе",
    )

    assert billing.granted == [(student.id, course.id, "оплата в кассе")]


async def test_an_address_nobody_signed_up_with_grants_nothing() -> None:
    """
    A typo is far more likely here than a person waiting for access.

    Creating an account for them would be worse than refusing: the student would then have
    a course open on an address they never proved is theirs.
    """
    service, billing, _ = _service()

    with pytest.raises(StudentNotFoundError):
        await service.grant(
            email="nobody@example.org", course_id=uuid7(), granted_by_id=uuid7(), reason=""
        )

    assert billing.granted == []


async def test_withdrawing_a_grant_that_does_not_exist_is_a_refusal() -> None:
    """A guessed identifier must not withdraw somebody else's access."""
    service, _, _ = _service()

    with pytest.raises(GrantNotFoundError):
        await service.revoke(uuid7())


async def test_a_withdrawn_grant_stays_on_the_list() -> None:
    """
    Access is history, not a switch.

    «Who opened this course, when, and who closed it» is asked months later, and a row that
    disappears on withdrawal cannot answer.
    """
    student = make_user(email="student@example.org")
    course = make_course(slug="therapy")
    entitlement = _grant(student=student, course=course, revoked=True)
    service, _, _ = _service([(entitlement, student, course)])

    page = await service.list_grants(course_id=None, limit=20, offset=0)

    assert page.total == 1
    assert page.items[0].revoked_at is not None


async def test_the_percentage_is_the_one_the_student_sees() -> None:
    """
    Both screens call the same function, and this is what keeps them agreeing.

    Two lectures of four and one work of two make three of six — half the course.
    """
    student = make_user(email="student@example.org")
    course = make_course(slug="therapy")
    service, _, _ = _service(
        [(_grant(student=student, course=course), student, course)],
        lessons=FakeLessonCounts(required=4, done=2),
        works=FakeWorkCounts(total=2, done=1),
    )

    page = await service.list_grants(course_id=None, limit=20, offset=0)

    assert page.items[0].progress_percent == 50


async def test_a_right_to_the_whole_catalogue_names_no_course() -> None:
    """
    There is no course to name and no percentage to count against one.

    The words for that case belong to the interface; this layer only says which case it is.
    """
    student = make_user(email="staff@example.org")
    service, _, _ = _service([(_grant(student=student, course=None), student, None)])

    page = await service.list_grants(course_id=None, limit=20, offset=0)

    assert page.items[0].course_id is None
    assert page.items[0].course_title == ""
    assert page.items[0].progress_percent == 0


async def test_the_reason_travels_to_the_screen() -> None:
    """What the course was opened for is the question this column exists to answer."""
    student = make_user(email="student@example.org")
    course = make_course(slug="therapy")
    service, _, _ = _service(
        [(_grant(student=student, course=course, reason="квитанция 4417"), student, course)]
    )

    page = await service.list_grants(course_id=None, limit=20, offset=0)

    assert page.items[0].reason == "квитанция 4417"


async def test_the_page_is_a_page_and_the_count_is_of_everything() -> None:
    """Otherwise «показать ещё» stops at the first page, or never stops at all."""
    student = make_user(email="student@example.org")
    course = make_course(slug="therapy")
    rows = [(_grant(student=student, course=course), student, course) for _ in range(5)]
    service, _, _ = _service(rows)

    page = await service.list_grants(course_id=None, limit=2, offset=0)

    assert len(page.items) == 2
    assert page.total == 5
