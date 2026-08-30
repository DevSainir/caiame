"""Serving a test to a student and grading what comes back."""

import pytest

from models.base import uuid7
from models.course_unit import CourseUnit
from models.enums import CourseUnitKind, QuestionKind, UnitStatus
from models.quiz import Quiz
from models.quiz_question import QuizOption, QuizQuestion
from schemas.quiz import AnswerIn
from services.quiz import NoAttemptsLeftError, QuizNotFoundError, QuizService
from tests.support.factories import make_course, make_unit
from tests.support.fakes import FakeCourseRepo, FakeQuizRepo, FakeSyllabusRepo


def _question(*, kind: QuestionKind, points: int, correct: int, options: int = 3) -> QuizQuestion:
    """One question with `correct` of its options marked as the answer."""
    question = QuizQuestion(
        id=uuid7(), quiz_id=uuid7(), position=1, text="Question", kind=kind, points=points
    )
    question.options = [  # type: ignore[attr-defined]  # carried by the fake, not by the model
        QuizOption(
            id=uuid7(),
            question_id=question.id,
            position=index + 1,
            text=f"Option {index}",
            is_correct=index < correct,
        )
        for index in range(options)
    ]
    return question


def _service(
    questions: list[QuizQuestion], *, passing_score: int = 1, max_attempts: int | None = None
) -> tuple[QuizService, CourseUnit]:
    """A service over one published course with one test on it."""
    course = make_course(slug="therapy")
    unit = make_unit(title="Test", kind=CourseUnitKind.TEST)
    unit.course_id = course.id
    quiz = Quiz(id=uuid7(), unit_id=unit.id, passing_score=passing_score, max_attempts=max_attempts)
    for question in questions:
        question.quiz_id = quiz.id
    syllabus = FakeSyllabusRepo([unit])
    return (
        QuizService(
            course_repo=FakeCourseRepo([course]),
            unit_repo=syllabus,
            quiz_repo=FakeQuizRepo(quiz, questions),
            progress_repo=syllabus,
        ),
        unit,
    )


async def test_the_answer_key_is_not_in_what_the_student_receives() -> None:
    """The student's schema has no such field, so there is no filter to forget."""
    question = _question(kind=QuestionKind.SINGLE, points=1, correct=1)
    service, unit = _service([question])

    quiz = await service.get_for_student(unit_id=unit.id, user_id=uuid7())

    assert quiz.questions[0].options
    assert not any(hasattr(option, "is_correct") for option in quiz.questions[0].options)


async def test_the_server_decides_the_score() -> None:
    """Points come from the question in the database, never from the browser."""
    question = _question(kind=QuestionKind.SINGLE, points=3, correct=1)
    service, unit = _service([question], passing_score=3)

    result = await service.submit(
        unit_id=unit.id,
        user_id=uuid7(),
        answers=[AnswerIn(question_id=question.id, option_ids=[question.options[0].id])],  # type: ignore[attr-defined]
    )

    assert result.score == 3
    assert result.max_score == 3
    assert result.passed is True


async def test_a_wrong_pick_earns_nothing() -> None:
    """A graded attempt is stored either way; a failed one is not an error."""
    question = _question(kind=QuestionKind.SINGLE, points=3, correct=1)
    service, unit = _service([question], passing_score=3)

    result = await service.submit(
        unit_id=unit.id,
        user_id=uuid7(),
        answers=[AnswerIn(question_id=question.id, option_ids=[question.options[2].id])],  # type: ignore[attr-defined]
    )

    assert result.score == 0
    assert result.passed is False


async def test_multiple_choice_is_all_or_nothing() -> None:
    """Two of three correct options earn no points: partial credit needs a stated rule."""
    question = _question(kind=QuestionKind.MULTIPLE, points=3, correct=3, options=4)
    service, unit = _service([question])
    options = question.options  # type: ignore[attr-defined]

    partial = await service.submit(
        unit_id=unit.id,
        user_id=uuid7(),
        answers=[AnswerIn(question_id=question.id, option_ids=[options[0].id, options[1].id])],
    )
    full = await service.submit(
        unit_id=unit.id,
        user_id=uuid7(),
        answers=[
            AnswerIn(
                question_id=question.id,
                option_ids=[options[0].id, options[1].id, options[2].id],
            )
        ],
    )

    assert partial.score == 0
    assert full.score == 3


async def test_an_extra_option_spoils_a_multiple_answer() -> None:
    """Everything correct plus one wrong is not «everything correct»."""
    question = _question(kind=QuestionKind.MULTIPLE, points=3, correct=2, options=3)
    service, unit = _service([question])
    options = question.options  # type: ignore[attr-defined]

    result = await service.submit(
        unit_id=unit.id,
        user_id=uuid7(),
        answers=[
            AnswerIn(
                question_id=question.id,
                option_ids=[options[0].id, options[1].id, options[2].id],
            )
        ],
    )

    assert result.score == 0


async def test_a_passed_test_closes_its_line_on_the_course_page() -> None:
    """The outline shows «finished» because grading said so, not because a page asked."""
    question = _question(kind=QuestionKind.SINGLE, points=2, correct=1)
    service, unit = _service([question], passing_score=2)
    student = uuid7()

    await service.submit(
        unit_id=unit.id,
        user_id=student,
        answers=[AnswerIn(question_id=question.id, option_ids=[question.options[0].id])],  # type: ignore[attr-defined]
    )

    assert service.progress_repo.statuses[unit.id] == str(UnitStatus.DONE)  # type: ignore[attr-defined]


async def test_the_attempt_limit_is_enforced() -> None:
    """A test with one attempt gives one attempt, and says so instead of grading again."""
    question = _question(kind=QuestionKind.SINGLE, points=1, correct=1)
    service, unit = _service([question], max_attempts=1)
    student = uuid7()
    answers = [AnswerIn(question_id=question.id, option_ids=[question.options[0].id])]  # type: ignore[attr-defined]

    await service.submit(unit_id=unit.id, user_id=student, answers=answers)

    with pytest.raises(NoAttemptsLeftError):
        await service.submit(unit_id=unit.id, user_id=student, answers=answers)


async def test_a_line_that_is_not_a_test_has_no_questions() -> None:
    """A module id in the address is a 404, not somebody else's questions."""
    service, _ = _service([_question(kind=QuestionKind.SINGLE, points=1, correct=1)])

    with pytest.raises(QuizNotFoundError):
        await service.get_for_student(unit_id=uuid7(), user_id=uuid7())
