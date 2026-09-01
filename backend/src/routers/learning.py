from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from core.deps import CurrentUser, LearningSvc, OptionalUser, QuizSvc
from schemas.learning import LessonDetailOut, LessonStatusOut, ModuleDetailOut
from schemas.quiz import AttemptResultOut, AttemptSubmitIn, QuizForStudentOut
from services.billing import AccessRequiredError
from services.learning import LessonNotFoundError, ModuleNotFoundError
from services.quiz import NoAttemptsLeftError, QuizNotFoundError

router = APIRouter(tags=["Learning"])

UnitId = Annotated[UUID, Path(description="Identifier of the outline line.")]
LessonId = Annotated[UUID, Path(description="Identifier of the lesson.")]


def _payment_required() -> HTTPException:
    """
    The answer when the account is known but the course is not open to it.

    402 rather than 403: the course exists, the person is signed in, and what is missing is
    the right to it — that is what the page turns into an offer rather than into a refusal.
    """
    return HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="access_required")


def _not_found(detail: str) -> HTTPException:
    """
    The one answer for anything the caller may not have.

    A missing module and a module of a draft course answer the same way on purpose: 404
    tells nothing about what exists, 403 tells that it does.
    """
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.get(
    "/modules/{unit_id}",
    response_model=ModuleDetailOut,
    responses={
        200: {"description": "The module with its lectures and the caller's progress."},
        404: {"description": "No such module in a published course."},
    },
)
async def get_module(svc: LearningSvc, viewer: OptionalUser, unit_id: UnitId) -> ModuleDetailOut:
    """Return one module of a published course."""
    try:
        return await svc.get_module(unit_id=unit_id, viewer=viewer)
    except ModuleNotFoundError as error:
        raise _not_found("module_not_found") from error


@router.get(
    "/lessons/{lesson_id}",
    response_model=LessonDetailOut,
    responses={
        200: {"description": "The lecture with the context shown above it."},
        401: {"description": "No valid access token."},
        402: {"description": "The course is not open to this account."},
        404: {"description": "No such lecture."},
    },
)
async def get_lesson(
    svc: LearningSvc, current_user: CurrentUser, lesson_id: LessonId
) -> LessonDetailOut:
    """
    Return one lecture.

    Behind the right to the course, unlike the outline above it: the plan of a course is a
    shop window and the material is the thing being sold.
    """
    try:
        return await svc.get_lesson(lesson_id=lesson_id, viewer=current_user)
    except LessonNotFoundError as error:
        raise _not_found("lesson_not_found") from error
    except AccessRequiredError as error:
        raise _payment_required() from error


@router.post(
    "/lessons/{lesson_id}/completion",
    response_model=LessonStatusOut,
    responses={
        200: {"description": "The lecture is marked finished; repeating this changes nothing."},
        401: {"description": "No valid access token."},
        402: {"description": "The course is not open to this account."},
        404: {"description": "No such lecture."},
    },
)
async def complete_lesson(
    svc: LearningSvc, current_user: CurrentUser, lesson_id: LessonId
) -> LessonStatusOut:
    """Mark a lecture finished for the signed-in student."""
    try:
        return await svc.complete_lesson(lesson_id=lesson_id, viewer=current_user)
    except LessonNotFoundError as error:
        raise _not_found("lesson_not_found") from error
    except AccessRequiredError as error:
        raise _payment_required() from error


@router.get(
    "/tests/{unit_id}",
    response_model=QuizForStudentOut,
    responses={
        200: {"description": "The test without its answer key."},
        401: {"description": "No valid access token."},
        402: {"description": "The course is not open to this account."},
        404: {"description": "No such test in a published course."},
    },
)
async def get_test(svc: QuizSvc, current_user: CurrentUser, unit_id: UnitId) -> QuizForStudentOut:
    """Return one test as a student may see it, together with their last result."""
    try:
        return await svc.get_for_student(unit_id=unit_id, viewer=current_user)
    except QuizNotFoundError as error:
        raise _not_found("test_not_found") from error
    except AccessRequiredError as error:
        raise _payment_required() from error


@router.post(
    "/tests/{unit_id}/attempts",
    response_model=AttemptResultOut,
    responses={
        200: {"description": "The attempt as the server graded it."},
        401: {"description": "No valid access token."},
        402: {"description": "The course is not open to this account."},
        404: {"description": "No such test in a published course."},
        409: {"description": "Every attempt this test allows has been spent."},
    },
)
async def submit_test(
    svc: QuizSvc, current_user: CurrentUser, unit_id: UnitId, payload: AttemptSubmitIn
) -> AttemptResultOut:
    """Grade an attempt at a test and store the result."""
    try:
        return await svc.submit(unit_id=unit_id, viewer=current_user, answers=payload.answers)
    except QuizNotFoundError as error:
        raise _not_found("test_not_found") from error
    except AccessRequiredError as error:
        raise _payment_required() from error
    except NoAttemptsLeftError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="no_attempts_left"
        ) from error
