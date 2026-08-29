from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.course_question import CourseQuestion
from schemas.question import QuestionListOut, QuestionOut
from services.course import CourseNotFoundError


class CourseLookup(Protocol):
    """The one thing the discussion block needs from the course storage."""

    async def get_published_by_slug(self, slug: str) -> Course | None:
        """Return one published course, or nothing."""
        ...


class QuestionReader(Protocol):
    """What the discussion block needs from storage."""

    async def list_for_course(self, course_id: UUID) -> Sequence[CourseQuestion]:
        """Every question of one course, in display order."""
        ...


class QuestionService:
    """The questions shown under one course."""

    def __init__(self, *, course_repo: CourseLookup, question_repo: QuestionReader) -> None:
        self.course_repo = course_repo
        self.question_repo = question_repo

    async def list_for_course(self, *, slug: str) -> QuestionListOut:
        """Return every question of a published course."""
        course = await self.course_repo.get_published_by_slug(slug)
        if course is None:
            raise CourseNotFoundError(slug)
        questions = await self.question_repo.list_for_course(course.id)
        return QuestionListOut(items=[QuestionOut.model_validate(item) for item in questions])
