from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from core.access import AdminUser
from core.deps import FaqSvc
from schemas.admin import FaqIn, FaqRowOut
from services.faq import CourseNotFoundForFaqError, FaqNotFoundError

router = APIRouter(prefix="/admin", tags=["Administration"])

CourseId = Annotated[UUID, Path(description="Identifier of the course.")]
QuestionId = Annotated[UUID, Path(description="Identifier of the question.")]

ANSWERS: dict[int | str, dict[str, object]] = {
    401: {"description": "No valid access token."},
    403: {"description": "Not an admin."},
    404: {"description": "No such course or question."},
}


def _missing() -> HTTPException:
    """The one answer for anything that is not there, or not there for this course."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="question_not_found")


@router.get("/courses/{course_id}/questions", response_model=list[FaqRowOut], responses={**ANSWERS})
async def list_questions(svc: FaqSvc, admin: AdminUser, course_id: CourseId) -> list[FaqRowOut]:
    """The questions shown under this course on its page."""
    try:
        return await svc.list_questions(course_id)
    except CourseNotFoundForFaqError as error:
        raise _missing() from error


@router.post(
    "/courses/{course_id}/questions",
    response_model=list[FaqRowOut],
    status_code=status.HTTP_201_CREATED,
    responses={**ANSWERS},
)
async def add_question(
    svc: FaqSvc, admin: AdminUser, course_id: CourseId, payload: FaqIn
) -> list[FaqRowOut]:
    """Add a question with its answer to the end of the list."""
    try:
        return await svc.add_question(course_id=course_id, payload=payload)
    except CourseNotFoundForFaqError as error:
        raise _missing() from error


@router.put(
    "/courses/{course_id}/questions/{question_id}",
    response_model=list[FaqRowOut],
    responses={**ANSWERS},
)
async def update_question(
    svc: FaqSvc,
    admin: AdminUser,
    course_id: CourseId,
    question_id: QuestionId,
    payload: FaqIn,
) -> list[FaqRowOut]:
    """Change the wording of a question or its answer."""
    try:
        return await svc.update_question(
            course_id=course_id, question_id=question_id, payload=payload
        )
    except (CourseNotFoundForFaqError, FaqNotFoundError) as error:
        raise _missing() from error


@router.delete(
    "/courses/{course_id}/questions/{question_id}",
    response_model=list[FaqRowOut],
    responses={**ANSWERS},
)
async def delete_question(
    svc: FaqSvc, admin: AdminUser, course_id: CourseId, question_id: QuestionId
) -> list[FaqRowOut]:
    """Take a question off the course page."""
    try:
        return await svc.delete_question(course_id=course_id, question_id=question_id)
    except (CourseNotFoundForFaqError, FaqNotFoundError) as error:
        raise _missing() from error
