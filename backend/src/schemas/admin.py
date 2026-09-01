from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.enums import AccessSource, CourseStatus, CourseUnitKind, LessonKind, QuestionKind


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


class CourseIn(BaseModel):
    """A course as the administration form sends it, new or changed."""

    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=20000)
    specialization_id: UUID
    accreditation_id: UUID | None = None
    credit_hours: int = Field(default=0, ge=0, le=10000)
    duration_hours: int = Field(default=0, ge=0, le=10000)
    # Money in minor units, never a fractional number: rounding errors in money show up in
    # the reconciliation with the bank rather than in a test.
    price_minor: int = Field(default=0, ge=0)


class CourseDetailOut(BaseModel):
    """Everything the course form shows, including what the catalogue never sends."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    summary: str
    description: str
    status: CourseStatus
    specialization_id: UUID
    accreditation_id: UUID | None
    credit_hours: int
    duration_hours: int
    price_minor: int
    currency: str
    students: int


class MaterialOut(BaseModel):
    """The file behind a lecture, as the editor lists it."""

    id: UUID
    original_name: str
    size_bytes: int
    duration_seconds: int
    content_type: str
    uploaded_at: datetime


class LessonDetailOut(BaseModel):
    """One lecture as its own editing screen shows it."""

    id: UUID
    unit_id: UUID
    position: int
    title: str
    description: str
    kind: LessonKind
    duration_minutes: int
    is_required: bool
    material: MaterialOut | None


class UploadStartIn(BaseModel):
    """What the browser tells the server before uploading a file."""

    file_name: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0)
    kind: LessonKind


class UploadTicketOut(BaseModel):
    """The one-file permission the browser uploads with."""

    media_id: UUID
    url: str
    content_type: str
    size_bytes: int


class UploadConfirmIn(BaseModel):
    """
    What the browser reports once the upload finished.

    The length is read from the file by the administrator's own browser, which holds the
    whole file. The player a student watches in is never asked for it: there the number
    decides whether a lecture counts as watched.
    """

    media_id: UUID
    duration_seconds: int = Field(default=0, ge=0)


class AccessGrantIn(BaseModel):
    """Opening a course for one student by hand."""

    email: str = Field(min_length=3, max_length=320)
    course_id: UUID | None = None
    reason: str = Field(default="", max_length=300)


class AccessRowOut(BaseModel):
    """One grant in the access list."""

    id: UUID
    student_name: str
    student_email: str
    course_id: UUID | None
    course_title: str
    source: AccessSource
    granted_at: datetime
    revoked_at: datetime | None
    reason: str
    progress_percent: int


class AccessPageOut(BaseModel):
    """A page of grants and whether there are more of them."""

    items: list[AccessRowOut]
    total: int


class OptionIn(BaseModel):
    """One answer option as the editor sends it."""

    text: str = Field(min_length=1, max_length=500)
    is_correct: bool = False


class OptionRowOut(BaseModel):
    """
    One option as the editor shows it, answer key included.

    Deliberately a different schema from the one a student receives: there the field simply
    does not exist, so there is no filtering step to forget.
    """

    id: UUID
    text: str
    is_correct: bool


class QuestionIn(BaseModel):
    """A question with its options."""

    text: str = Field(min_length=1, max_length=2000)
    kind: QuestionKind
    points: int = Field(default=1, ge=1, le=100)
    options: list[OptionIn] = Field(min_length=2, max_length=10)


class QuestionRowOut(BaseModel):
    """One question of a test as the editor lists it."""

    id: UUID
    position: int
    text: str
    kind: QuestionKind
    points: int
    # Whether somebody has already answered it. Such a question is replaced rather than
    # edited, and the screen has to know which of the two it is offering.
    is_answered: bool
    options: list[OptionRowOut]


class QuizSettingsIn(BaseModel):
    """What counts as a pass and how many attempts a student gets."""

    passing_score: int = Field(ge=0, le=10000)
    # Empty means «as many as they like».
    max_attempts: int | None = Field(default=None, ge=1, le=100)


class QuizEditorOut(BaseModel):
    """The whole test as its editing screen shows it."""

    unit_id: UUID
    title: str
    passing_score: int
    max_attempts: int | None
    max_score: int
    questions: list[QuestionRowOut]
