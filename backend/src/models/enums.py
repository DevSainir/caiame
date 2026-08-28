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


class DifficultyLevel(StrEnum):
    """How much prior practice a course expects. Fixed set, so it is an enum and not a table."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
