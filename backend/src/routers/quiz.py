from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from core.access import AdminUser
from core.deps import QuestionBankSvc
from schemas.admin import QuestionIn, QuizEditorOut, QuizSettingsIn
from services.question_bank import (
    InvalidQuestionError,
    NoSuchTestError,
    QuestionAnsweredError,
    QuestionNotFoundError,
)

router = APIRouter(prefix="/admin", tags=["Administration"])

CourseId = Annotated[UUID, Path(description="Identifier of the course.")]
UnitId = Annotated[UUID, Path(description="Identifier of the programme line.")]
QuestionId = Annotated[UUID, Path(description="Identifier of the question.")]

FORBIDDEN: dict[int | str, dict[str, object]] = {
    401: {"description": "No valid access token."},
    403: {"description": "Not an admin."},
}
# The whole question editor answers the same three ways, so the answers are written once.
QUIZ_ERRORS: dict[int | str, dict[str, object]] = {
    404: {"description": "No such test or question in this course."},
    409: {"description": "The question has been answered, or it cannot be graded."},
}


def _missing(detail: str) -> HTTPException:
    """The one answer for anything that is not there, or not there for this course."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    """The answer when the request is understood but the state of things refuses it."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


@router.get(
    "/courses/{course_id}/tests/{unit_id}",
    response_model=QuizEditorOut,
    responses={**FORBIDDEN, **QUIZ_ERRORS},
)
async def get_test(
    svc: QuestionBankSvc, admin: AdminUser, course_id: CourseId, unit_id: UnitId
) -> QuizEditorOut:
    """The test with its questions and the answer key, as the editor shows it."""
    try:
        return await svc.get_editor(course_id=course_id, unit_id=unit_id)
    except NoSuchTestError as error:
        raise _missing("test_not_found") from error


@router.put(
    "/courses/{course_id}/tests/{unit_id}",
    response_model=QuizEditorOut,
    responses={**FORBIDDEN, **QUIZ_ERRORS},
)
async def update_test(
    svc: QuestionBankSvc,
    admin: AdminUser,
    course_id: CourseId,
    unit_id: UnitId,
    payload: QuizSettingsIn,
) -> QuizEditorOut:
    """Change the passing score and the number of attempts."""
    try:
        return await svc.update_settings(course_id=course_id, unit_id=unit_id, payload=payload)
    except NoSuchTestError as error:
        raise _missing("test_not_found") from error


@router.post(
    "/courses/{course_id}/tests/{unit_id}/questions",
    response_model=QuizEditorOut,
    responses={**FORBIDDEN, **QUIZ_ERRORS},
)
async def add_question(
    svc: QuestionBankSvc,
    admin: AdminUser,
    course_id: CourseId,
    unit_id: UnitId,
    payload: QuestionIn,
) -> QuizEditorOut:
    """Add a question to the end of the test."""
    try:
        return await svc.add_question(course_id=course_id, unit_id=unit_id, payload=payload)
    except NoSuchTestError as error:
        raise _missing("test_not_found") from error
    except InvalidQuestionError as error:
        raise _conflict(str(error)) from error


@router.put(
    "/courses/{course_id}/tests/{unit_id}/questions/{question_id}",
    response_model=QuizEditorOut,
    responses={**FORBIDDEN, **QUIZ_ERRORS},
)
async def update_question(
    svc: QuestionBankSvc,
    admin: AdminUser,
    course_id: CourseId,
    unit_id: UnitId,
    question_id: QuestionId,
    payload: QuestionIn,
) -> QuizEditorOut:
    """
    Change a question nobody has answered yet.

    A question with answers behind it is refused with 409: changing its wording would turn
    a stored verdict into one nobody can explain. Such a question is replaced instead, and
    that is a separate route because it is a separate decision.
    """
    try:
        return await svc.update_question(
            course_id=course_id, unit_id=unit_id, question_id=question_id, payload=payload
        )
    except (NoSuchTestError, QuestionNotFoundError) as error:
        raise _missing("question_not_found") from error
    except QuestionAnsweredError as error:
        raise _conflict("question_already_answered") from error
    except InvalidQuestionError as error:
        raise _conflict(str(error)) from error


@router.post(
    "/courses/{course_id}/tests/{unit_id}/questions/{question_id}/replacement",
    response_model=QuizEditorOut,
    responses={**FORBIDDEN, **QUIZ_ERRORS},
)
async def replace_question(
    svc: QuestionBankSvc,
    admin: AdminUser,
    course_id: CourseId,
    unit_id: UnitId,
    question_id: QuestionId,
    payload: QuestionIn,
) -> QuizEditorOut:
    """Put a new question in place of one that has already been answered."""
    try:
        return await svc.replace_question(
            course_id=course_id, unit_id=unit_id, question_id=question_id, payload=payload
        )
    except (NoSuchTestError, QuestionNotFoundError) as error:
        raise _missing("question_not_found") from error
    except InvalidQuestionError as error:
        raise _conflict(str(error)) from error


@router.delete(
    "/courses/{course_id}/tests/{unit_id}/questions/{question_id}",
    response_model=QuizEditorOut,
    responses={**FORBIDDEN, **QUIZ_ERRORS},
)
async def delete_question(
    svc: QuestionBankSvc,
    admin: AdminUser,
    course_id: CourseId,
    unit_id: UnitId,
    question_id: QuestionId,
) -> QuizEditorOut:
    """Take a question out of the test without touching the attempts that used it."""
    try:
        return await svc.remove_question(
            course_id=course_id, unit_id=unit_id, question_id=question_id
        )
    except (NoSuchTestError, QuestionNotFoundError) as error:
        raise _missing("question_not_found") from error
