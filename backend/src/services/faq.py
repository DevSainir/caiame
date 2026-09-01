"""
The questions and answers shown under a course.

Editorial text, not a conversation: both halves are written by the academy. Until now they
could only be changed by re-seeding the catalogue, which on a live server also means
touching everything else the seeder writes.
"""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.course_question import CourseQuestion
from schemas.admin import FaqIn, FaqRowOut


class CourseNotFoundForFaqError(Exception):
    """No such course."""


class FaqNotFoundError(Exception):
    """No such question in this course."""


class CourseLookup(Protocol):
    """Courses, drafts included: their questions are edited before publication too."""

    async def get_course(self, course_id: UUID) -> Course | None: ...


class FaqStore(Protocol):
    """Everything this editor needs from storage."""

    async def list_for_course(self, course_id: UUID) -> Sequence[CourseQuestion]: ...
    async def get(self, question_id: UUID) -> CourseQuestion | None: ...
    async def add(self, question: CourseQuestion) -> CourseQuestion: ...
    async def delete(self, question: CourseQuestion) -> None: ...
    async def next_position(self, course_id: UUID) -> int: ...
    async def flush(self) -> None: ...


class FaqService:
    """Reading and editing the questions under one course."""

    def __init__(self, *, course_repo: CourseLookup, question_repo: FaqStore) -> None:
        self.course_repo = course_repo
        self.question_repo = question_repo

    async def list_questions(self, course_id: UUID) -> list[FaqRowOut]:
        """Every question of one course, in the order the page shows them."""
        await self._course(course_id)
        return [_row(item) for item in await self.question_repo.list_for_course(course_id)]

    async def add_question(self, *, course_id: UUID, payload: FaqIn) -> list[FaqRowOut]:
        """Add a question to the end of the list."""
        course = await self._course(course_id)
        await self.question_repo.add(
            CourseQuestion(
                course_id=course.id,
                position=await self.question_repo.next_position(course.id),
                question=payload.question,
                answer=payload.answer,
            )
        )
        return await self.list_questions(course_id)

    async def update_question(
        self, *, course_id: UUID, question_id: UUID, payload: FaqIn
    ) -> list[FaqRowOut]:
        """Change the wording of a question or its answer."""
        question = await self._question(course_id, question_id)
        question.question = payload.question
        question.answer = payload.answer
        await self.question_repo.flush()
        return await self.list_questions(course_id)

    async def delete_question(self, *, course_id: UUID, question_id: UUID) -> list[FaqRowOut]:
        """Remove a question from the course page."""
        question = await self._question(course_id, question_id)
        await self.question_repo.delete(question)
        return await self.list_questions(course_id)

    async def _course(self, course_id: UUID) -> Course:
        """The course, or a refusal that says nothing about what exists."""
        course = await self.course_repo.get_course(course_id)
        if course is None:
            raise CourseNotFoundForFaqError(course_id)
        return course

    async def _question(self, course_id: UUID, question_id: UUID) -> CourseQuestion:
        """A question that belongs to this very course."""
        question = await self.question_repo.get(question_id)
        if question is None or question.course_id != course_id:
            raise FaqNotFoundError(question_id)
        return question


def _row(question: CourseQuestion) -> FaqRowOut:
    """One question as the editor lists it."""
    return FaqRowOut(
        id=question.id,
        position=question.position,
        question=question.question,
        answer=question.answer,
    )
