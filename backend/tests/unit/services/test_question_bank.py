"""
Editing a test that people have already taken.

The one rule this module exists for: a question somebody has answered is never edited. Get
it wrong and a finished attempt stops being explainable — the database says «wrong» while
the screen shows a question the student answered correctly.
"""

from collections.abc import Sequence
from uuid import UUID

import pytest

from models.base import uuid7
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, QuestionKind
from models.quiz import Quiz
from models.quiz_question import QuizOption, QuizQuestion
from schemas.admin import OptionIn, QuestionIn
from services.question_bank import (
    InvalidQuestionError,
    NoSuchTestError,
    QuestionAnsweredError,
    QuestionBankService,
)
from tests.support.factories import make_unit


class FakeQuizRepo:
    """In-memory test storage that keeps the same rules about deletion as the SQL does."""

    def __init__(self, quiz: Quiz | None = None, answered: set[UUID] | None = None) -> None:
        self.quiz = quiz
        self.questions: list[QuizQuestion] = []
        self.options: list[QuizOption] = []
        self.answered = answered or set()

    async def get_by_unit(self, unit_id: UUID) -> Quiz | None:
        """The test of one outline line."""
        return self.quiz if self.quiz and self.quiz.unit_id == unit_id else None

    async def create_quiz(self, quiz: Quiz) -> Quiz:
        """Attach a test to a line."""
        quiz.id = uuid7()
        self.quiz = quiz
        return quiz

    async def list_questions(self, quiz_id: UUID) -> Sequence[QuizQuestion]:
        """Live questions only — a removed one stays out of new attempts."""
        return [
            question
            for question in self.questions
            if question.quiz_id == quiz_id and question.deleted_at is None
        ]

    async def list_options(self, question_ids: Sequence[UUID]) -> Sequence[QuizOption]:
        """Options of the given questions."""
        return [option for option in self.options if option.question_id in set(question_ids)]

    async def answered_question_ids(self, question_ids: Sequence[UUID]) -> set[UUID]:
        """Which of these questions somebody has already answered."""
        return {question_id for question_id in question_ids if question_id in self.answered}

    async def get_question(self, question_id: UUID) -> QuizQuestion | None:
        """One live question."""
        return next(
            (
                question
                for question in self.questions
                if question.id == question_id and question.deleted_at is None
            ),
            None,
        )

    async def add_question(self, question: QuizQuestion, options: Sequence[QuizOption]) -> None:
        """Insert a question with its options."""
        question.id = uuid7()
        self.questions.append(question)
        for option in options:
            option.id = uuid7()
            option.question_id = question.id
            self.options.append(option)

    async def replace_options(self, question: QuizQuestion, options: Sequence[QuizOption]) -> None:
        """Swap the options of a question."""
        self.options = [option for option in self.options if option.question_id != question.id]
        for option in options:
            option.id = uuid7()
            option.question_id = question.id
            self.options.append(option)

    async def next_question_position(self, quiz_id: UUID) -> int:
        """After the last live question."""
        live = await self.list_questions(quiz_id)
        return max((question.position for question in live), default=0) + 1

    async def flush(self) -> None:
        """Nothing to push in memory."""


class FakeUnitRepo:
    """The outline, with one line in it."""

    def __init__(self, unit: CourseUnit) -> None:
        self.unit = unit

    async def get_unit(self, unit_id: UUID) -> CourseUnit | None:
        """One line by its id."""
        return self.unit if self.unit.id == unit_id else None


def _question(text: str = "Сколько часов в программе?") -> QuestionIn:
    """A well-formed question with one correct option."""
    return QuestionIn(
        text=text,
        kind=QuestionKind.SINGLE,
        points=1,
        options=[
            OptionIn(text="72", is_correct=True),
            OptionIn(text="144", is_correct=False),
        ],
    )


def _service(
    *, answered: set[UUID] | None = None
) -> tuple[QuestionBankService, CourseUnit, FakeQuizRepo]:
    """A service over one course with one test line on it."""
    unit = make_unit(title="Тестирование", kind=CourseUnitKind.TEST)
    unit.course_id = uuid7()
    quiz_repo = FakeQuizRepo(Quiz(id=uuid7(), unit_id=unit.id, passing_score=1), answered)
    return QuestionBankService(unit_repo=FakeUnitRepo(unit), quiz_repo=quiz_repo), unit, quiz_repo


async def test_a_question_nobody_answered_is_edited_in_place() -> None:
    """Until somebody takes the test, editing is just editing."""
    service, unit, _ = _service()
    editor = await service.add_question(
        course_id=unit.course_id, unit_id=unit.id, payload=_question()
    )

    updated = await service.update_question(
        course_id=unit.course_id,
        unit_id=unit.id,
        question_id=editor.questions[0].id,
        payload=_question("Сколько часов занимает цикл?"),
    )

    assert len(updated.questions) == 1
    assert updated.questions[0].text == "Сколько часов занимает цикл?"


async def test_an_answered_question_is_not_edited() -> None:
    """
    The refusal that keeps finished attempts explainable.

    Without it the stored verdict and the question on screen stop matching, and nobody can
    say afterwards what the student was actually asked.
    """
    service, unit, repo = _service()
    editor = await service.add_question(
        course_id=unit.course_id, unit_id=unit.id, payload=_question()
    )
    repo.answered.add(editor.questions[0].id)

    with pytest.raises(QuestionAnsweredError):
        await service.update_question(
            course_id=unit.course_id,
            unit_id=unit.id,
            question_id=editor.questions[0].id,
            payload=_question("Переписанный вопрос"),
        )


async def test_replacing_keeps_the_old_question_out_of_new_attempts() -> None:
    """
    Replacement is the way out: the old question stays behind old attempts and disappears
    from new ones.
    """
    service, unit, repo = _service()
    editor = await service.add_question(
        course_id=unit.course_id, unit_id=unit.id, payload=_question()
    )
    old_id = editor.questions[0].id
    repo.answered.add(old_id)

    after = await service.replace_question(
        course_id=unit.course_id,
        unit_id=unit.id,
        question_id=old_id,
        payload=_question("Новая формулировка"),
    )

    assert [question.text for question in after.questions] == ["Новая формулировка"]
    assert next(q for q in repo.questions if q.id == old_id).deleted_at is not None


async def test_a_removed_question_leaves_the_test_but_not_the_history() -> None:
    """Soft removal, always: attempts point at the question."""
    service, unit, repo = _service()
    editor = await service.add_question(
        course_id=unit.course_id, unit_id=unit.id, payload=_question()
    )

    after = await service.remove_question(
        course_id=unit.course_id, unit_id=unit.id, question_id=editor.questions[0].id
    )

    assert after.questions == []
    assert len(repo.questions) == 1


async def test_a_question_without_a_correct_option_is_refused() -> None:
    """Every student would get it wrong, and nobody would know why."""
    service, unit, _ = _service()

    with pytest.raises(InvalidQuestionError):
        await service.add_question(
            course_id=unit.course_id,
            unit_id=unit.id,
            payload=QuestionIn(
                text="Вопрос без ответа",
                kind=QuestionKind.SINGLE,
                points=1,
                options=[OptionIn(text="раз"), OptionIn(text="два")],
            ),
        )


async def test_a_single_answer_question_cannot_have_two_correct_options() -> None:
    """Otherwise it is graded by a rule nobody wrote down."""
    service, unit, _ = _service()

    with pytest.raises(InvalidQuestionError):
        await service.add_question(
            course_id=unit.course_id,
            unit_id=unit.id,
            payload=QuestionIn(
                text="Один ответ или два?",
                kind=QuestionKind.SINGLE,
                points=1,
                options=[
                    OptionIn(text="раз", is_correct=True),
                    OptionIn(text="два", is_correct=True),
                ],
            ),
        )


async def test_a_module_is_not_a_test() -> None:
    """A guessed identifier must not open the question editor of somebody else's line."""
    unit = make_unit(title="Модуль", kind=CourseUnitKind.MODULE)
    unit.course_id = uuid7()
    service = QuestionBankService(unit_repo=FakeUnitRepo(unit), quiz_repo=FakeQuizRepo())

    with pytest.raises(NoSuchTestError):
        await service.get_editor(course_id=unit.course_id, unit_id=unit.id)
