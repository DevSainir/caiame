"""
The one decision that stands between paid material and everybody else.

Every case here is a way to be wrong in the expensive direction: an account with no right,
a right that was withdrawn, a right that ran out. All of them have to answer «no», and the
absence of a right has to answer «no» rather than «probably fine».
"""

from datetime import UTC, datetime, timedelta

import pytest

from models.base import uuid7
from models.entitlement import Entitlement
from models.enums import AccessSource, UserRole
from services.billing import AccessRequiredError, BillingService
from tests.support.factories import make_user
from tests.support.fakes import FakeEntitlementRepo


def _entitlement(
    *,
    user_id: object,
    course_id: object,
    revoked: bool = False,
    ends_at: datetime | None = None,
    starts_at: datetime | None = None,
) -> Entitlement:
    """One grant, in whatever state the case needs."""
    return Entitlement(
        id=uuid7(),
        user_id=user_id,
        course_id=course_id,
        source=AccessSource.MANUAL,
        starts_at=starts_at or datetime.now(UTC) - timedelta(days=1),
        ends_at=ends_at,
        revoked_at=datetime.now(UTC) if revoked else None,
        granted_by_id=None,
        reason="paid at the office",
    )


async def test_a_visitor_without_an_account_has_no_access() -> None:
    """Nobody is the plainest «no» there is, and it must not fall through to yes."""
    service = BillingService(entitlement_repo=FakeEntitlementRepo())

    assert await service.has_access(user=None, course_id=uuid7()) is False


async def test_a_student_without_a_grant_has_no_access() -> None:
    """Signing up is not buying: an account on its own opens nothing."""
    student = make_user()
    service = BillingService(entitlement_repo=FakeEntitlementRepo())

    assert await service.has_access(user=student, course_id=uuid7()) is False


async def test_a_granted_course_opens() -> None:
    """The whole point: a live grant lets this student into this course."""
    student = make_user()
    course_id = uuid7()
    service = BillingService(
        entitlement_repo=FakeEntitlementRepo(
            [_entitlement(user_id=student.id, course_id=course_id)]
        )
    )

    assert await service.has_access(user=student, course_id=course_id) is True


async def test_a_grant_for_another_course_opens_nothing_here() -> None:
    """One purchase is one course, not the catalogue."""
    student = make_user()
    service = BillingService(
        entitlement_repo=FakeEntitlementRepo([_entitlement(user_id=student.id, course_id=uuid7())])
    )

    assert await service.has_access(user=student, course_id=uuid7()) is False


async def test_a_withdrawn_grant_closes_the_course() -> None:
    """Withdrawal is a column, not a delete — and the column has to be read."""
    student = make_user()
    course_id = uuid7()
    service = BillingService(
        entitlement_repo=FakeEntitlementRepo(
            [_entitlement(user_id=student.id, course_id=course_id, revoked=True)]
        )
    )

    assert await service.has_access(user=student, course_id=course_id) is False


async def test_an_expired_grant_closes_the_course_at_once() -> None:
    """
    Expiry is decided when the question is asked.

    No nightly job switches anything off: such a job is always late by its own interval,
    and that interval is free access.
    """
    student = make_user()
    course_id = uuid7()
    service = BillingService(
        entitlement_repo=FakeEntitlementRepo(
            [
                _entitlement(
                    user_id=student.id,
                    course_id=course_id,
                    ends_at=datetime.now(UTC) - timedelta(minutes=1),
                )
            ]
        )
    )

    assert await service.has_access(user=student, course_id=course_id) is False


async def test_a_grant_for_the_whole_catalogue_opens_any_course() -> None:
    """A grant with no course named is how a subscription will look."""
    student = make_user()
    service = BillingService(
        entitlement_repo=FakeEntitlementRepo([_entitlement(user_id=student.id, course_id=None)])
    )

    assert await service.has_access(user=student, course_id=uuid7()) is True


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.INSTRUCTOR])
async def test_staff_open_the_material_they_are_responsible_for(role: UserRole) -> None:
    """An administrator publishes lectures and a teacher works with them."""
    staff = make_user(email="staff@example.org", role=role)
    service = BillingService(entitlement_repo=FakeEntitlementRepo())

    assert await service.has_access(user=staff, course_id=uuid7()) is True


async def test_requiring_access_refuses_instead_of_answering() -> None:
    """The callers that serve material need a refusal they cannot accidentally ignore."""
    service = BillingService(entitlement_repo=FakeEntitlementRepo())

    with pytest.raises(AccessRequiredError):
        await service.require_access(user=make_user(), course_id=uuid7())


async def test_a_manual_grant_records_who_gave_it_and_why() -> None:
    """A right with nobody's name on it cannot be explained when somebody asks."""
    repo = FakeEntitlementRepo()
    service = BillingService(entitlement_repo=repo)
    admin = make_user(email="admin@example.org", role=UserRole.ADMIN)
    student = make_user()

    granted = await service.grant(
        user_id=student.id,
        course_id=uuid7(),
        granted_by_id=admin.id,
        reason="paid by bank transfer",
    )

    assert granted.granted_by_id == admin.id
    assert granted.reason == "paid by bank transfer"
    assert granted.source is AccessSource.MANUAL


async def test_granting_the_same_course_twice_gives_one_right() -> None:
    """
    The button gets pressed twice — by two people, or by one who did not see the first row.

    Two live rows for one course are two lines on the access screen, and withdrawing the
    line somebody sees leaves the course open through the line they do not see.
    """
    repo = FakeEntitlementRepo()
    service = BillingService(entitlement_repo=repo)
    admin = make_user(email="admin@example.org", role=UserRole.ADMIN)
    student = make_user()
    course_id = uuid7()

    first = await service.grant(
        user_id=student.id, course_id=course_id, granted_by_id=admin.id, reason="paid"
    )
    second = await service.grant(
        user_id=student.id, course_id=course_id, granted_by_id=admin.id, reason="paid again"
    )

    assert second.id == first.id
    assert len(repo.entitlements) == 1


async def test_withdrawing_a_repeated_grant_actually_closes_the_course() -> None:
    """The whole point of the rule above, stated as the thing that used to break."""
    repo = FakeEntitlementRepo()
    service = BillingService(entitlement_repo=repo)
    admin = make_user(email="admin@example.org", role=UserRole.ADMIN)
    student = make_user()
    course_id = uuid7()
    await service.grant(
        user_id=student.id, course_id=course_id, granted_by_id=admin.id, reason="paid"
    )
    granted = await service.grant(
        user_id=student.id, course_id=course_id, granted_by_id=admin.id, reason="paid"
    )

    await service.revoke(granted)

    assert await service.has_access(user=student, course_id=course_id) is False


async def test_a_right_to_the_catalogue_is_not_the_same_right_as_one_course() -> None:
    """Withdrawing one course must not look like withdrawing everything, or the reverse."""
    repo = FakeEntitlementRepo()
    service = BillingService(entitlement_repo=repo)
    admin = make_user(email="admin@example.org", role=UserRole.ADMIN)
    student = make_user()
    course_id = uuid7()

    everything = await service.grant(
        user_id=student.id, course_id=None, granted_by_id=admin.id, reason="staff"
    )
    one = await service.grant(
        user_id=student.id, course_id=course_id, granted_by_id=admin.id, reason="paid"
    )

    assert one.id != everything.id
    assert len(repo.entitlements) == 2
