"""
The right to open a course: one table, one question, one answer.

Everything else in the application asks `has_access` and nothing else looks at where a
right came from. As soon as two places decide this question, they start to disagree, and
the disagreement is found by a person writing «I paid and the video will not open».

There is no payment provider here yet, and this module does not pretend otherwise: rights
are granted by an administrator by hand. When orders arrive, they will write the same rows
through this same service, and every caller stays as it is.
"""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from models.entitlement import Entitlement
from models.enums import AccessSource, UserRole
from models.user import User

# An administrator publishes the material and a teacher works with it; both have to be able
# to open what they are responsible for. Written once, here, rather than as an extra `or`
# in every place that asks about access.
STAFF_ROLES = (UserRole.ADMIN, UserRole.INSTRUCTOR)


class AccessRequiredError(Exception):
    """This account may not open this course's material."""


class EntitlementStore(Protocol):
    """What the billing service needs from the entitlement storage."""

    async def has_live(self, *, user_id: UUID, course_id: UUID, at: datetime) -> bool:
        """Whether a live, unrevoked right to this course exists at this moment."""
        ...

    async def get(self, entitlement_id: UUID) -> Entitlement | None:
        """One grant by its id."""
        ...

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
        """Write down a granted right."""
        ...

    async def revoke(self, entitlement: Entitlement, *, at: datetime) -> Entitlement:
        """Withdraw a right, keeping the record of it."""
        ...


class BillingService:
    """The only place that decides whether an account may open a course."""

    def __init__(self, *, entitlement_repo: EntitlementStore) -> None:
        self.entitlement_repo = entitlement_repo

    async def has_access(self, *, user: User | None, course_id: UUID) -> bool:
        """
        Whether this account may open the material of this course.

        Closed by default. No account, no right, an expired right or a withdrawn one all
        answer «no»; a failure to answer at all raises and the request fails, which is also
        not «yes». There is no branch here that opens the material because something could
        not be checked.
        """
        if user is None:
            return False
        if user.role in STAFF_ROLES:
            return True
        return await self.entitlement_repo.has_live(
            user_id=user.id, course_id=course_id, at=datetime.now(UTC)
        )

    async def require_access(self, *, user: User | None, course_id: UUID) -> None:
        """The same question where the answer «no» has to stop the request."""
        if not await self.has_access(user=user, course_id=course_id):
            raise AccessRequiredError(course_id)

    async def grant(
        self,
        *,
        user_id: UUID,
        course_id: UUID | None,
        granted_by_id: UUID,
        reason: str,
        source: AccessSource = AccessSource.MANUAL,
    ) -> Entitlement:
        """
        Give an account the right to a course, or to everything.

        Who granted it and why are not optional: a right with nobody's name against it
        cannot be explained later, and «who opened this course for free» is exactly the
        question that gets asked.
        """
        return await self.entitlement_repo.create(
            user_id=user_id,
            course_id=course_id,
            source=source,
            granted_by_id=granted_by_id,
            reason=reason,
            ends_at=None,
        )

    async def revoke(self, entitlement: Entitlement) -> Entitlement:
        """
        Withdraw a right.

        The study record and every fact of progress under it stay untouched: the student
        stops being able to open lectures and keeps their history, so that access given
        back later continues from the same place instead of from the beginning.
        """
        return await self.entitlement_repo.revoke(entitlement, at=datetime.now(UTC))
