"""
The questions shown under a course.

Editorial text, and the only thing here that can go quietly wrong is the ownership check:
an identifier from another course must not edit somebody else's page.
"""

from collections.abc import Sequence
from uuid import UUID

import pytest

from models.base import uuid7
from models.course import Course
from models.course_question import CourseQuestion
from schemas.admin import FaqIn
from services.faq import CourseNotFoundForFaqError, FaqNotFoundError, FaqService
from tests.support.factories import make_course


class FakeCourses:
    """Courses by id, drafts included."""

    def __init__(self, courses: list[Course]) -> None:
        self.courses = courses

    async def get_course(self, course_id: UUID) -> Course | None:
        """One course, whatever its status."""
        return next((course for course in self.courses if course.id == course_id), None)


class FakeQuestions:
    """In-memory questions of every course."""

    def __init__(self, questions: list[CourseQuestion]) -> None:
        self.questions = questions

    async def list_for_course(self, course_id: UUID) -> Sequence[CourseQuestion]:
        """In display order."""
        return sorted(
            (item for item in self.questions if item.course_id == course_id),
            key=lambda item: item.position,
        )

    async def get(self, question_id: UUID) -> CourseQuestion | None:
        """One question by id."""
        return next((item for item in self.questions if item.id == question_id), None)

    async def add(self, question: CourseQuestion) -> CourseQuestion:
        """Insert a question."""
        question.id = uuid7()
        self.questions.append(question)
        return question

    async def delete(self, question: CourseQuestion) -> None:
        """Remove a question."""
        self.questions.remove(question)

    async def next_position(self, course_id: UUID) -> int:
        """After the last one."""
        found = await self.list_for_course(course_id)
        return max((item.position for item in found), default=0) + 1

    async def flush(self) -> None:
        """Nothing to push in memory."""


def _service() -> tuple[FaqService, Course, Course, CourseQuestion]:
    """Two courses, and one question that belongs to the second of them."""
    mine = make_course(slug="therapy")
    other = make_course(slug="surgery")
    question = CourseQuestion(
        id=uuid7(), course_id=other.id, position=1, question="Чужой вопрос", answer="Чужой ответ"
    )
    service = FaqService(
        course_repo=FakeCourses([mine, other]), question_repo=FakeQuestions([question])
    )
    return service, mine, other, question


async def test_a_question_of_another_course_is_not_found() -> None:
    """A guessed identifier must not edit somebody else's page."""
    service, mine, _, question = _service()

    with pytest.raises(FaqNotFoundError):
        await service.update_question(
            course_id=mine.id,
            question_id=question.id,
            payload=FaqIn(question="Подменённый", answer="Подменённый"),
        )


async def test_a_question_is_added_to_the_end() -> None:
    """Order is decided by the server: a page that renumbers itself is a page that jumps."""
    service, mine, _, _ = _service()

    await service.add_question(course_id=mine.id, payload=FaqIn(question="Первый", answer="Ответ"))
    rows = await service.add_question(
        course_id=mine.id, payload=FaqIn(question="Второй", answer="Ответ")
    )

    assert [row.question for row in rows] == ["Первый", "Второй"]


async def test_an_unknown_course_has_no_questions() -> None:
    """404 rather than an empty list: an empty list reads as «this course has none»."""
    service, _, _, _ = _service()

    with pytest.raises(CourseNotFoundForFaqError):
        await service.list_questions(uuid7())
