from uuid import UUID

from pydantic import BaseModel


class MyCourseOut(BaseModel):
    """
    One course a student has started, as their own list shows it.

    Both the percentage and whether the course is open right now are counted at the moment
    of asking. A stored percentage drifts from the facts silently, and access that was
    checked once at enrolment stops meaning anything the day it ends.
    """

    id: UUID
    slug: str
    title: str
    cover_url: str | None
    progress_percent: int
    is_completed: bool
    # Whether the course is open right now. The study record outlives access, together with
    # all of the progress under it, so the course stays in this list while its lectures stop
    # opening.
    has_access: bool
    # Where to carry on from, when the student has already opened something.
    continue_lesson_id: UUID | None
