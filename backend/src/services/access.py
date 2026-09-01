"""
The administration's view of who may open what.

Granting and withdrawing themselves belong to `billing` — it is the only place that writes
the right — and this service exists for the screen around them: the list of grants with the
student, the course and how far that student has got.

There is no payment provider yet. Until there is, every right on this screen is one an
administrator gave by hand, which is why the reason and the name of whoever gave it are
part of the row rather than a detail hidden in the table.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.entitlement import Entitlement
from models.enums import AccessSource
from models.user import User
from schemas.admin import AccessPageOut, AccessRowOut
from services.learning import completion_percent


class StudentNotFoundError(Exception):
    """No account with this address, so there is nobody to grant a right to."""


class GrantNotFoundError(Exception):
    """No such grant."""


class EntitlementList(Protocol):
    """What this screen needs from the entitlement storage."""

    async def list_grants(
        self, *, course_id: UUID | None, limit: int, offset: int
    ) -> Sequence[tuple[Entitlement, User, Course | None]]: ...

    async def count_grants(self, *, course_id: UUID | None) -> int: ...

    async def get(self, entitlement_id: UUID) -> Entitlement | None: ...


class Granting(Protocol):
    """The service that owns the right itself."""

    async def grant(
        self,
        *,
        user_id: UUID,
        course_id: UUID | None,
        granted_by_id: UUID,
        reason: str,
        source: AccessSource = AccessSource.MANUAL,
    ) -> Entitlement: ...

    async def revoke(self, entitlement: Entitlement) -> Entitlement: ...


class StudentLookup(Protocol):
    """Finding the account a right is about."""

    async def get_by_email(self, email: str) -> User | None: ...


class ProgressCounts(Protocol):
    """The four numbers the percentage is made of, for many students at once."""

    async def required_totals(self, course_ids: Sequence[UUID]) -> dict[UUID, int]: ...

    async def done_by_student(
        self, *, course_ids: Sequence[UUID], user_ids: Sequence[UUID]
    ) -> dict[tuple[UUID, UUID], int]: ...


class WorkCounts(Protocol):
    """The same for the works of a course — assignments and tests."""

    async def work_totals(self, course_ids: Sequence[UUID]) -> dict[UUID, int]: ...

    async def done_works_by_student(
        self, *, course_ids: Sequence[UUID], user_ids: Sequence[UUID]
    ) -> dict[tuple[UUID, UUID], int]: ...


class AccessService:
    """The list of grants, and the two operations the screen offers over it."""

    def __init__(
        self,
        *,
        entitlement_repo: EntitlementList,
        billing: Granting,
        user_repo: StudentLookup,
        lesson_repo: ProgressCounts,
        unit_repo: WorkCounts,
    ) -> None:
        self.entitlement_repo = entitlement_repo
        self.billing = billing
        self.user_repo = user_repo
        self.lesson_repo = lesson_repo
        self.unit_repo = unit_repo

    async def list_grants(
        self, *, course_id: UUID | None, limit: int, offset: int
    ) -> AccessPageOut:
        """One page of grants, each with the progress of that student in that course."""
        rows = await self.entitlement_repo.list_grants(
            course_id=course_id, limit=limit, offset=offset
        )
        total = await self.entitlement_repo.count_grants(course_id=course_id)
        progress = await self._progress(rows)
        return AccessPageOut(items=[self._row(row, progress) for row in rows], total=total)

    async def grant(
        self, *, email: str, course_id: UUID | None, granted_by_id: UUID, reason: str
    ) -> None:
        """Open a course for an existing account, named by the address it signed up with."""
        student = await self.user_repo.get_by_email(email)
        if student is None:
            raise StudentNotFoundError(email)
        await self.billing.grant(
            user_id=student.id,
            course_id=course_id,
            granted_by_id=granted_by_id,
            reason=reason,
        )

    async def revoke(self, grant_id: UUID) -> None:
        """
        Close a course again.

        Progress and the study record are untouched by this on purpose: the student stops
        being able to open lectures and keeps everything they did, so access given back
        later continues from the same place.
        """
        entitlement = await self.entitlement_repo.get(grant_id)
        if entitlement is None:
            raise GrantNotFoundError(grant_id)
        await self.billing.revoke(entitlement)

    async def _progress(
        self, rows: Sequence[tuple[Entitlement, User, Course | None]]
    ) -> dict[tuple[UUID, UUID], int]:
        """
        The percentage for every student on this page, in four queries rather than in four
        per row.
        """
        course_ids = [course.id for _, _, course in rows if course is not None]
        user_ids = [student.id for _, student, _ in rows]
        if not course_ids or not user_ids:
            return {}

        lesson_totals = await self.lesson_repo.required_totals(course_ids)
        work_totals = await self.unit_repo.work_totals(course_ids)
        lessons_done = await self.lesson_repo.done_by_student(
            course_ids=course_ids, user_ids=user_ids
        )
        works_done = await self.unit_repo.done_works_by_student(
            course_ids=course_ids, user_ids=user_ids
        )
        return {
            (user_id, course_id): completion_percent(
                lessons_done=lessons_done.get((user_id, course_id), 0),
                lessons_total=lesson_totals.get(course_id, 0),
                works_done=works_done.get((user_id, course_id), 0),
                works_total=work_totals.get(course_id, 0),
            )
            for user_id in user_ids
            for course_id in course_ids
        }

    @staticmethod
    def _row(
        row: tuple[Entitlement, User, Course | None],
        progress: dict[tuple[UUID, UUID], int],
    ) -> AccessRowOut:
        """One grant as the table shows it."""
        entitlement, student, course = row
        return AccessRowOut(
            id=entitlement.id,
            student_name=student.full_name,
            student_email=student.email,
            course_id=course.id if course else None,
            # Empty when the right covers the whole catalogue. The words for that case are
            # the interface's business; this layer only says which of the two cases it is.
            course_title=course.title if course else "",
            source=entitlement.source,
            granted_at=entitlement.starts_at,
            revoked_at=entitlement.revoked_at,
            reason=entitlement.reason,
            progress_percent=(
                progress.get((student.id, course.id), 0) if course is not None else 0
            ),
        )


def is_live(entitlement: Entitlement, *, at: datetime) -> bool:
    """Whether a grant is in force at this moment. Used for the label on the row."""
    if entitlement.revoked_at is not None:
        return False
    if entitlement.ends_at is not None and entitlement.ends_at <= at:
        return False
    return entitlement.starts_at <= at
