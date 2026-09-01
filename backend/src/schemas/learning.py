from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import LessonKind, UnitStatus


class CourseRefOut(BaseModel):
    """Where the student is, one level up. Enough for a heading and a link back."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str


class ModuleRefOut(BaseModel):
    """The module a lesson belongs to."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str


class LessonRowOut(BaseModel):
    """One lecture in the list of a module."""

    id: UUID
    position: int
    title: str
    kind: LessonKind
    duration_minutes: int
    status: UnitStatus


class ModuleDetailOut(BaseModel):
    """A module with its lectures, as its own page shows it."""

    id: UUID
    title: str
    summary: str
    description: str
    # Whether this visitor may open the lectures. The list of them is shown either way —
    # it is part of what the course offers — and this is what decides between a link and a
    # closed lock next to each line.
    has_access: bool
    course: CourseRefOut
    lessons: list[LessonRowOut]


class LessonDetailOut(BaseModel):
    """
    One lecture, with everything the page needs and nothing else.

    The link to the material is signed and expires, so it is produced for this request and
    for this account. Nothing here is built by the page: it receives an address or it
    receives nothing, and nothing means the lecture is not ready yet.
    """

    id: UUID
    title: str
    description: str
    kind: LessonKind
    duration_minutes: int
    material_url: str | None
    status: UnitStatus
    course: CourseRefOut
    module: ModuleRefOut


class LessonStatusOut(BaseModel):
    """The answer to «mark it finished»: the status the lesson has now."""

    status: UnitStatus
