from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.enums import CourseStatus, CourseUnitKind, LessonKind


class CourseRowOut(BaseModel):
    """One course in the administration list — including the ones nobody may see yet."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    status: CourseStatus
    credit_hours: int
    specialization: str
    modules: int
    lessons: int


class LessonRowOut(BaseModel):
    """One lecture in the programme tree."""

    id: UUID
    position: int
    title: str
    kind: LessonKind
    duration_minutes: int
    is_required: bool
    has_material: bool


class UnitRowOut(BaseModel):
    """One line of the programme: a module with its lectures, an assignment or a test."""

    id: UUID
    kind: CourseUnitKind
    position: int
    title: str
    summary: str
    lessons: list[LessonRowOut]


class CourseTreeOut(BaseModel):
    """The whole programme of one course, as the editor shows it."""

    id: UUID
    slug: str
    title: str
    status: CourseStatus
    modules: list[UnitRowOut]
    activities: list[UnitRowOut]


class UnitIn(BaseModel):
    """A module, an assignment or a test as the editor sends it."""

    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=300)
    kind: CourseUnitKind


class UnitUpdateIn(BaseModel):
    """What may be changed about an existing line without changing what it is."""

    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=300)


class LessonIn(BaseModel):
    """A lecture as the editor sends it."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    kind: LessonKind
    duration_minutes: int = Field(default=0, ge=0, le=1000)
    is_required: bool = True


class MoveIn(BaseModel):
    """
    A move by one step, up or down.

    Not «here is the new order of everything»: two rows would then race to claim the same
    position. One step is one swap inside a single transaction.
    """

    direction: int = Field(description="-1 to move up, 1 to move down")


class CourseStatusIn(BaseModel):
    """Publishing or unpublishing a course."""

    status: CourseStatus
