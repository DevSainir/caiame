from uuid import UUID

from pydantic import BaseModel

from models.enums import CourseUnitKind, UnitStatus


class CourseUnitOut(BaseModel):
    """One line of the outline, with the status of the account that asked."""

    id: UUID
    kind: CourseUnitKind
    position: int
    title: str
    summary: str
    status: UnitStatus


class SyllabusOut(BaseModel):
    """
    The outline of one course, split the way the page shows it.

    `progress_percent` is counted here from the statuses above and is never stored: a saved
    percentage drifts away from the facts without anything failing.
    """

    modules: list[CourseUnitOut]
    activities: list[CourseUnitOut]
    progress_percent: int
    # Whether the course is open to this visitor. The outline is shown to everybody — it is
    # a shop window — but the button under it has to say different things to a guest, to an
    # enrolled student, and to somebody who has signed up but not been let in yet.
    has_access: bool
