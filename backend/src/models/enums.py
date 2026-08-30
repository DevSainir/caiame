from enum import StrEnum


class UserRole(StrEnum):
    """Who the account belongs to. The access ladder in `security` reads this, routes do not."""

    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class CourseStatus(StrEnum):
    """Publication state. Only `published` courses are visible in the catalogue."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Audience(StrEnum):
    """
    Which profession a specialization admits.

    Written on the specialization and not on the course: a specialization is accredited for
    one kind of professional, and every course inside it inherits that audience.
    """

    DOCTOR = "doctor"
    NURSE = "nurse"


class CourseUnitKind(StrEnum):
    """
    What a line in the syllabus is.

    One table rather than three: the course page shows modules and works in the same list
    shape, and the difference that matters here is which card they land in. The real
    lessons, attempts and grading live in their own domains — see `learning-domain` and
    `assessments` — and this outline does not pretend to be them.
    """

    MODULE = "module"
    ASSIGNMENT = "assignment"
    TEST = "test"


class UnitStatus(StrEnum):
    """How far one student got in one unit. The course percentage is derived from these."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class LessonKind(StrEnum):
    """
    What a lesson is made of, and therefore what «finished» means for it.

    The rule per kind lives in one place — `services/learning.py` — and not in an `if` in
    three of them. A new kind is a new completion rule, a new payload and a new component;
    without all three it is not a kind.
    """

    VIDEO = "video"
    PDF = "pdf"


class QuestionKind(StrEnum):
    """How many options a question expects. Grading differs, so the type is stored."""

    SINGLE = "single"
    MULTIPLE = "multiple"
