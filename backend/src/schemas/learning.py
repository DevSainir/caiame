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
    course: CourseRefOut
    lessons: list[LessonRowOut]


class LessonDetailOut(BaseModel):
    """
    One lecture, with everything the page needs and nothing else.

    The link to the material is a plain path today. When storage moves behind signed links
    (see `media-video`), only this field changes shape — the page already treats it as
    something it receives rather than something it builds.
    """

    id: UUID
    title: str
    description: str
    kind: LessonKind
    duration_minutes: int
    asset_url: str
    status: UnitStatus
    course: CourseRefOut
    module: ModuleRefOut


class LessonStatusOut(BaseModel):
    """The answer to «mark it finished»: the status the lesson has now."""

    status: UnitStatus
