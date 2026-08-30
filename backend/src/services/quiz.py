from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from models.course import Course
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, QuestionKind, UnitStatus
from models.quiz import Quiz
from models.quiz_attempt import QuizAttempt, QuizAttemptAnswer
from models.quiz_question import QuizOption, QuizQuestion
from schemas.learning import CourseRefOut
from schemas.quiz import (
    AnswerIn,
    AttemptResultOut,
    OptionForStudentOut,
    QuestionForStudentOut,
    QuizForStudentOut,
)


class QuizNotFoundError(Exception):
    """No test behind this line of the outline."""


class NoAttemptsLeftError(Exception):
    """The student has spent every attempt this test allows."""


class CourseByIdReader(Protocol):
    """What the test page needs from the course storage."""

    async def get_published_by_id(self, course_id: UUID) -> Course | None:
        """Return one published course by its id, or nothing."""
        ...


class UnitReader(Protocol):
    """What the test page needs from the outline storage."""

    async def get_unit(self, unit_id: UUID) -> CourseUnit | None:
        """One line of the outline by its id."""
        ...


class QuizReader(Protocol):
    """What the test page needs from the quiz storage."""

    async def get_by_unit(self, unit_id: UUID) -> Quiz | None:
        """The test attached to one line of the outline."""
        ...

    async def list_questions(self, quiz_id: UUID) -> Sequence[QuizQuestion]:
        """Live questions of one test."""
        ...

    async def list_options(self, question_ids: Sequence[UUID]) -> Sequence[QuizOption]:
        """Options of the given questions."""
        ...

    async def latest_attempt(self, *, user_id: UUID, quiz_id: UUID) -> QuizAttempt | None:
        """The student's most recent attempt."""
        ...

    async def count_attempts(self, *, user_id: UUID, quiz_id: UUID) -> int:
        """How many attempts the student has spent."""
        ...

    async def add_attempt(self, attempt: QuizAttempt, answers: Sequence[QuizAttemptAnswer]) -> None:
        """Store a graded attempt."""
        ...


class UnitProgressWriter(Protocol):
    """The one thing grading needs from the progress storage."""

    async def mark_unit(self, *, user_id: UUID, unit_id: UUID, status: UnitStatus) -> None:
        """Record how far a student got in one unit of the outline."""
        ...


class QuizService:
    """Serving a test to a student and grading what comes back."""

    def __init__(
        self,
        *,
        course_repo: CourseByIdReader,
        unit_repo: UnitReader,
        quiz_repo: QuizReader,
        progress_repo: UnitProgressWriter,
    ) -> None:
        self.course_repo = course_repo
        self.unit_repo = unit_repo
        self.quiz_repo = quiz_repo
        self.progress_repo = progress_repo

    async def get_for_student(self, *, unit_id: UUID, user_id: UUID | None) -> QuizForStudentOut:
        """
        The test as a student may see it.

        Assembled into schemas that have no `is_correct` field at all, so no filtering step
        exists to be forgotten later.
        """
        unit, quiz, course = await self._resolve(unit_id)
        questions = await self.quiz_repo.list_questions(quiz.id)
        options = await self.quiz_repo.list_options([question.id for question in questions])
        by_question: dict[UUID, list[QuizOption]] = {}
        for option in options:
            by_question.setdefault(option.question_id, []).append(option)

        spent = (
            await self.quiz_repo.count_attempts(user_id=user_id, quiz_id=quiz.id)
            if user_id is not None
            else 0
        )
        last = (
            await self.quiz_repo.latest_attempt(user_id=user_id, quiz_id=quiz.id)
            if user_id is not None
            else None
        )
        return QuizForStudentOut(
            unit_id=unit.id,
            title=unit.title,
            description=unit.summary,
            passing_score=quiz.passing_score,
            max_score=sum(question.points for question in questions),
            attempts_left=None if quiz.max_attempts is None else max(0, quiz.max_attempts - spent),
            questions=[
                QuestionForStudentOut(
                    id=question.id,
                    position=question.position,
                    text=question.text,
                    kind=question.kind,
                    points=question.points,
                    options=[
                        OptionForStudentOut(id=option.id, text=option.text)
                        for option in by_question.get(question.id, [])
                    ],
                )
                for question in questions
            ],
            last_attempt=_result(last),
            course=CourseRefOut.model_validate(course),
            module=None,
        )

    async def submit(
        self, *, unit_id: UUID, user_id: UUID, answers: list[AnswerIn]
    ) -> AttemptResultOut:
        """
        Grade one attempt on the server and store it.

        Nothing about the outcome is taken from the client: the score, the verdict and the
        number of the attempt are all computed here from what is in the database. A `score`
        sent by the browser is not a shortcut, it is a student grading themselves.
        """
        unit, quiz, _ = await self._resolve(unit_id)
        spent = await self.quiz_repo.count_attempts(user_id=user_id, quiz_id=quiz.id)
        if quiz.max_attempts is not None and spent >= quiz.max_attempts:
            raise NoAttemptsLeftError(unit_id)

        questions = await self.quiz_repo.list_questions(quiz.id)
        options = await self.quiz_repo.list_options([question.id for question in questions])
        correct: dict[UUID, set[UUID]] = {}
        for option in options:
            if option.is_correct:
                correct.setdefault(option.question_id, set()).add(option.id)

        chosen = {answer.question_id: set(answer.option_ids) for answer in answers}
        graded: list[QuizAttemptAnswer] = []
        score = 0
        for question in questions:
            picked = chosen.get(question.id, set())
            is_correct = _is_correct(question.kind, picked, correct.get(question.id, set()))
            awarded = question.points if is_correct else 0
            score += awarded
            graded.append(
                QuizAttemptAnswer(
                    question_id=question.id,
                    selected_option_ids=[str(option_id) for option_id in sorted(picked)],
                    is_correct=is_correct,
                    points_awarded=awarded,
                )
            )

        max_score = sum(question.points for question in questions)
        attempt = QuizAttempt(
            user_id=user_id,
            quiz_id=quiz.id,
            number=spent + 1,
            submitted_at=datetime.now(UTC),
            score=score,
            max_score=max_score,
            passed=score >= quiz.passing_score,
        )
        await self.quiz_repo.add_attempt(attempt, graded)

        # A passed attempt closes the line on the course page; a failed one leaves it
        # started. Passing once is not undone by a worse attempt later.
        status = UnitStatus.DONE if attempt.passed else UnitStatus.IN_PROGRESS
        await self.progress_repo.mark_unit(user_id=user_id, unit_id=unit.id, status=status)
        return AttemptResultOut(
            number=attempt.number,
            score=attempt.score,
            max_score=attempt.max_score,
            passed=attempt.passed,
        )

    async def _resolve(self, unit_id: UUID) -> tuple[CourseUnit, Quiz, Course]:
        """The unit, its test and the published course they belong to — or a refusal."""
        unit = await self.unit_repo.get_unit(unit_id)
        if unit is None or unit.kind is not CourseUnitKind.TEST:
            raise QuizNotFoundError(unit_id)
        quiz = await self.quiz_repo.get_by_unit(unit.id)
        if quiz is None:
            raise QuizNotFoundError(unit_id)
        course = await self.course_repo.get_published_by_id(unit.course_id)
        if course is None:
            raise QuizNotFoundError(unit_id)
        return unit, quiz, course


def _is_correct(kind: QuestionKind, picked: set[UUID], correct: set[UUID]) -> bool:
    """
    Whether one answer earns its points.

    `multiple` is all-or-nothing: partial credit looks fairer but needs a stated rule for
    what a wrong extra option costs, and an unstated rule reads as a broken system.
    """
    if not picked:
        return False
    if kind is QuestionKind.SINGLE:
        return len(picked) == 1 and picked <= correct
    return picked == correct


def _result(attempt: QuizAttempt | None) -> AttemptResultOut | None:
    """The last attempt as the page shows it, if there was one."""
    if attempt is None:
        return None
    return AttemptResultOut(
        number=attempt.number,
        score=attempt.score,
        max_score=attempt.max_score,
        passed=attempt.passed,
    )
