"""
Editing the questions of a test.

One rule shapes this whole module: a question somebody has already answered is never
edited. Change the wording and the stored verdict stops being explainable — the database
says «wrong» while the screen shows a question the student answered correctly. Such a
question is replaced instead: a new one takes its place and the old one is marked removed,
which leaves finished attempts intact and keeps new ones honest.

The answer key lives here in the open, unlike everywhere else: this is the screen where an
administrator marks which options are correct. The student's side has its own schemas
without the field at all.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, QuestionKind
from models.quiz import Quiz
from models.quiz_question import QuizOption, QuizQuestion
from schemas.admin import (
    OptionRowOut,
    QuestionIn,
    QuestionRowOut,
    QuizEditorOut,
    QuizSettingsIn,
)


class NoSuchTestError(Exception):
    """
    No such test in this course.

    Named this way round rather than `TestNotFoundError` because pytest collects anything
    starting with «Test» and would spend every run warning that it cannot.
    """


class QuestionNotFoundError(Exception):
    """No such question in this test."""


class QuestionAnsweredError(Exception):
    """Somebody has answered this question, so it may be replaced but not edited."""


class InvalidQuestionError(Exception):
    """A question that cannot be graded: no options, or no correct answer among them."""


class UnitReader(Protocol):
    """The outline, as this service reads it."""

    async def get_unit(self, unit_id: UUID) -> CourseUnit | None: ...


class QuizStore(Protocol):
    """Everything the question editor needs from storage."""

    async def get_by_unit(self, unit_id: UUID) -> Quiz | None: ...
    async def create_quiz(self, quiz: Quiz) -> Quiz: ...
    async def list_questions(self, quiz_id: UUID) -> Sequence[QuizQuestion]: ...
    async def list_options(self, question_ids: Sequence[UUID]) -> Sequence[QuizOption]: ...
    async def answered_question_ids(self, question_ids: Sequence[UUID]) -> set[UUID]: ...
    async def get_question(self, question_id: UUID) -> QuizQuestion | None: ...
    async def add_question(self, question: QuizQuestion, options: Sequence[QuizOption]) -> None: ...
    async def replace_options(
        self, question: QuizQuestion, options: Sequence[QuizOption]
    ) -> None: ...
    async def next_question_position(self, quiz_id: UUID) -> int: ...
    async def flush(self) -> None: ...


class QuestionBankService:
    """The administration's side of a test: its settings and its questions."""

    def __init__(self, *, unit_repo: UnitReader, quiz_repo: QuizStore) -> None:
        self.unit_repo = unit_repo
        self.quiz_repo = quiz_repo

    async def get_editor(self, *, course_id: UUID, unit_id: UUID) -> QuizEditorOut:
        """
        The test as its editing screen shows it, answer key included.

        Each question also says whether it can still be changed, so the screen offers
        «edit» or «replace» rather than letting somebody find out by being refused.
        """
        quiz = await self._quiz(course_id, unit_id)
        questions = await self.quiz_repo.list_questions(quiz.id)
        options = await self.quiz_repo.list_options([question.id for question in questions])
        answered = await self.quiz_repo.answered_question_ids(
            [question.id for question in questions]
        )
        by_question: dict[UUID, list[QuizOption]] = {}
        for option in options:
            by_question.setdefault(option.question_id, []).append(option)

        return QuizEditorOut(
            unit_id=unit_id,
            title=(await self._unit(course_id, unit_id)).title,
            passing_score=quiz.passing_score,
            max_attempts=quiz.max_attempts,
            max_score=sum(question.points for question in questions),
            questions=[
                QuestionRowOut(
                    id=question.id,
                    position=question.position,
                    text=question.text,
                    kind=question.kind,
                    points=question.points,
                    is_answered=question.id in answered,
                    options=[
                        OptionRowOut(id=option.id, text=option.text, is_correct=option.is_correct)
                        for option in by_question.get(question.id, [])
                    ],
                )
                for question in questions
            ],
        )

    async def update_settings(
        self, *, course_id: UUID, unit_id: UUID, payload: QuizSettingsIn
    ) -> QuizEditorOut:
        """Change what counts as a pass and how many attempts a student gets."""
        quiz = await self._quiz(course_id, unit_id)
        quiz.passing_score = payload.passing_score
        quiz.max_attempts = payload.max_attempts
        await self.quiz_repo.flush()
        return await self.get_editor(course_id=course_id, unit_id=unit_id)

    async def add_question(
        self, *, course_id: UUID, unit_id: UUID, payload: QuestionIn
    ) -> QuizEditorOut:
        """Add a question to the end of the test."""
        quiz = await self._quiz(course_id, unit_id)
        _validate(payload)
        position = await self.quiz_repo.next_question_position(quiz.id)
        await self.quiz_repo.add_question(
            QuizQuestion(
                quiz_id=quiz.id,
                position=position,
                text=payload.text,
                kind=payload.kind,
                points=payload.points,
            ),
            _options(payload),
        )
        return await self.get_editor(course_id=course_id, unit_id=unit_id)

    async def update_question(
        self, *, course_id: UUID, unit_id: UUID, question_id: UUID, payload: QuestionIn
    ) -> QuizEditorOut:
        """
        Change a question nobody has answered yet.

        A question with answers behind it is refused here rather than quietly replaced:
        replacing is a different act with a different result, and the person doing it should
        be the one who decides.
        """
        quiz = await self._quiz(course_id, unit_id)
        question = await self._question(quiz.id, question_id)
        _validate(payload)
        if await self._is_answered(question.id):
            raise QuestionAnsweredError(question_id)

        question.text = payload.text
        question.kind = payload.kind
        question.points = payload.points
        await self.quiz_repo.replace_options(question, _options(payload))
        return await self.get_editor(course_id=course_id, unit_id=unit_id)

    async def replace_question(
        self, *, course_id: UUID, unit_id: UUID, question_id: UUID, payload: QuestionIn
    ) -> QuizEditorOut:
        """
        Put a new question in the place of one that has been answered.

        The old question keeps standing behind the attempts that used it and disappears
        from new ones. Nothing is recalculated: a finished attempt stays exactly as it was
        graded.
        """
        quiz = await self._quiz(course_id, unit_id)
        question = await self._question(quiz.id, question_id)
        _validate(payload)

        await self.quiz_repo.add_question(
            QuizQuestion(
                quiz_id=quiz.id,
                position=question.position,
                text=payload.text,
                kind=payload.kind,
                points=payload.points,
            ),
            _options(payload),
        )
        question.deleted_at = datetime.now(UTC)
        await self.quiz_repo.flush()
        return await self.get_editor(course_id=course_id, unit_id=unit_id)

    async def remove_question(
        self, *, course_id: UUID, unit_id: UUID, question_id: UUID
    ) -> QuizEditorOut:
        """
        Take a question out of the test.

        Soft, always: attempts point at it. A removed question does not affect new attempts
        and does not recalculate old ones.
        """
        quiz = await self._quiz(course_id, unit_id)
        question = await self._question(quiz.id, question_id)
        question.deleted_at = datetime.now(UTC)
        await self.quiz_repo.flush()
        return await self.get_editor(course_id=course_id, unit_id=unit_id)

    async def _unit(self, course_id: UUID, unit_id: UUID) -> CourseUnit:
        """A test line that belongs to this very course."""
        unit = await self.unit_repo.get_unit(unit_id)
        if unit is None or unit.course_id != course_id or unit.kind is not CourseUnitKind.TEST:
            raise NoSuchTestError(unit_id)
        return unit

    async def _quiz(self, course_id: UUID, unit_id: UUID) -> Quiz:
        """
        The test behind a line of the outline, created on first use.

        A test line without settings is a line nobody can put a question on, and making the
        administrator press «create test» on a line that already says «test» is a step that
        exists only because of how the tables are laid out.
        """
        unit = await self._unit(course_id, unit_id)
        quiz = await self.quiz_repo.get_by_unit(unit.id)
        if quiz is None:
            quiz = await self.quiz_repo.create_quiz(
                Quiz(unit_id=unit.id, passing_score=1, max_attempts=None)
            )
        return quiz

    async def _question(self, quiz_id: UUID, question_id: UUID) -> QuizQuestion:
        """A question that belongs to this very test."""
        question = await self.quiz_repo.get_question(question_id)
        if question is None or question.quiz_id != quiz_id:
            raise QuestionNotFoundError(question_id)
        return question

    async def _is_answered(self, question_id: UUID) -> bool:
        """Whether anybody has already answered this question."""
        return question_id in await self.quiz_repo.answered_question_ids([question_id])


def _validate(payload: QuestionIn) -> None:
    """
    Refuse a question that cannot be graded.

    Both cases are silent otherwise: a question with no correct option is one every student
    gets wrong, and a single-answer question with two correct ones is graded by a rule
    nobody wrote down.
    """
    correct = [option for option in payload.options if option.is_correct]
    if not correct:
        raise InvalidQuestionError("no_correct_option")
    if payload.kind is QuestionKind.SINGLE and len(correct) > 1:
        raise InvalidQuestionError("single_answer_with_many_correct")


def _options(payload: QuestionIn) -> list[QuizOption]:
    """The options of a question, numbered in the order they were sent."""
    return [
        QuizOption(position=index, text=option.text, is_correct=option.is_correct)
        for index, option in enumerate(payload.options, start=1)
    ]
