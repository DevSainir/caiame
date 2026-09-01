from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from core.access import AdminUser, StaffUser
from core.deps import GradingSvc, ReviewerSvc
from schemas.admin import ReviewerIn, ReviewerRowOut
from schemas.assignment import QueuePageOut, ReviewIn, SubmissionDetailOut
from services.grading import (
    AlreadyDecidedError,
    NotAReviewerError,
    SelfReviewError,
    SubmissionNotFoundError,
)
from services.reviewers import (
    CourseNotFoundForReviewersError,
    NotStaffError,
    ReviewerNotFoundError,
)

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
    """
    Work waiting to be looked at, the one that has waited longest first.

    A teacher sees the courses they were put on; an administrator sees everything.
    """
    return await svc.queue(viewer=staff, course_id=course_id, limit=limit, offset=offset)


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
        403: {"description": "Not a reviewer of the course this work belongs to."},
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
    except NotAReviewerError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not_a_reviewer_of_this_course"
        ) from error
    except AlreadyDecidedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already_reviewed"
        ) from error


@router.get(
    "/courses/{course_id}/reviewers",
    response_model=list[ReviewerRowOut],
    responses={**FORBIDDEN, 404: {"description": "No such course."}},
)
async def list_reviewers(
    svc: ReviewerSvc,
    admin: AdminUser,
    course_id: Annotated[UUID, Path(description="Identifier of the course.")],
) -> list[ReviewerRowOut]:
    """Who checks the work sent in for this course."""
    try:
        return await svc.list_reviewers(course_id)
    except CourseNotFoundForReviewersError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="course_not_found"
        ) from error


@router.post(
    "/courses/{course_id}/reviewers",
    response_model=list[ReviewerRowOut],
    responses={
        **FORBIDDEN,
        404: {"description": "No such course."},
        409: {"description": "This address belongs to a student, or to nobody."},
    },
)
async def add_reviewer(
    svc: ReviewerSvc,
    admin: AdminUser,
    course_id: Annotated[UUID, Path(description="Identifier of the course.")],
    payload: ReviewerIn,
) -> list[ReviewerRowOut]:
    """
    Put a member of staff on this course.

    Only staff: a student put on a course would be reading their coursemates' work.
    """
    try:
        return await svc.add_reviewer(course_id=course_id, email=payload.email)
    except CourseNotFoundForReviewersError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="course_not_found"
        ) from error
    except NotStaffError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="not_a_member_of_staff"
        ) from error


@router.delete(
    "/courses/{course_id}/reviewers/{assignment_id}",
    response_model=list[ReviewerRowOut],
    responses={**FORBIDDEN, 404: {"description": "No such course or assignment."}},
)
async def remove_reviewer(
    svc: ReviewerSvc,
    admin: AdminUser,
    course_id: Annotated[UUID, Path(description="Identifier of the course.")],
    assignment_id: Annotated[UUID, Path(description="Identifier of the assignment.")],
) -> list[ReviewerRowOut]:
    """Take somebody off this course. The reviews they wrote stay where they are."""
    try:
        return await svc.remove_reviewer(course_id=course_id, assignment_id=assignment_id)
    except (CourseNotFoundForReviewersError, ReviewerNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="reviewer_not_found"
        ) from error
