from uuid import UUID

from pydantic import BaseModel

from models.enums import QuestionKind
from schemas.learning import CourseRefOut, ModuleRefOut


class OptionForStudentOut(BaseModel):
    """
    One option as the student sees it.

    There is no `is_correct` in this class, and that is the whole point: the key cannot
    leak through a schema that has nowhere to put it.
    """

    id: UUID
    text: str


class QuestionForStudentOut(BaseModel):
    """One question as the student sees it, with its weight but without the answer."""

    id: UUID
    position: int
    text: str
    kind: QuestionKind
    points: int
    options: list[OptionForStudentOut]


class AttemptResultOut(BaseModel):
    """What one graded attempt came to. Which questions were right is not in here yet."""

    number: int
    score: int
    max_score: int
    passed: bool


class QuizForStudentOut(BaseModel):
    """A test as its page shows it: the questions, the rules and the last result."""

    unit_id: UUID
    title: str
    description: str
    passing_score: int
    max_score: int
    attempts_left: int | None
    questions: list[QuestionForStudentOut]
    last_attempt: AttemptResultOut | None
    course: CourseRefOut
    module: ModuleRefOut | None


class AnswerIn(BaseModel):
    """What the student picked in one question."""

    question_id: UUID
    option_ids: list[UUID]


class AttemptSubmitIn(BaseModel):
    """A whole attempt, sent at once when the student presses «submit»."""

    answers: list[AnswerIn]
