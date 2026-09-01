from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from core.access import StaffUser
from core.deps import GradingSvc
from schemas.assignment import QueuePageOut, ReviewIn, SubmissionDetailOut
from services.grading import AlreadyDecidedError, SelfReviewError, SubmissionNotFoundError

router = APIRouter(prefix="/admin", tags=["Administration"])

SubmissionId = Annotated[UUID, Path(description="Identifier of the submission.")]

FORBIDDEN: dict[int | str, dict[str, object]] = {
    401: {"description": "No valid access token."},
    403: {"description": "Not a member of staff."},
}


@router.get("/submissions", response_model=QueuePageOut, responses={**FORBIDDEN})
async def review_queue(
    svc: GradingSvc,
    staff: StaffUser,
    course_id: Annotated[UUID | None, Query(description="Only work from this course.")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> QueuePageOut:
    """Work waiting to be looked at, the one that has waited longest first."""
    return await svc.queue(course_id=course_id, limit=limit, offset=offset)


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionDetailOut,
    responses={**FORBIDDEN, 404: {"description": "No such submission."}},
)
async def get_submission(
    svc: GradingSvc, staff: StaffUser, submission_id: SubmissionId
) -> SubmissionDetailOut:
    """One piece of work with its files and everything the student sent before it."""
    try:
        return await svc.get_submission(submission_id)
    except SubmissionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="submission_not_found"
        ) from error


@router.post(
    "/submissions/{submission_id}/review",
    response_model=SubmissionDetailOut,
    responses={
        **FORBIDDEN,
        404: {"description": "No such submission."},
        409: {"description": "Own work, or an attempt that has already been marked."},
    },
)
async def review_submission(
    svc: GradingSvc, staff: StaffUser, submission_id: SubmissionId, payload: ReviewIn
) -> SubmissionDetailOut:
    """
    Mark one attempt.

    Accepting closes the line on the course page; sending back for revision opens the next
    attempt and leaves everything already written where it is.
    """
    try:
        return await svc.review(submission_id=submission_id, reviewer=staff, payload=payload)
    except SubmissionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="submission_not_found"
        ) from error
    except SelfReviewError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="cannot_review_own_work"
        ) from error
    except AlreadyDecidedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already_reviewed"
        ) from error
