from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from core.deps import AssignmentSvc, CurrentUser, MediaSvc
from schemas.admin import UploadTicketOut
from schemas.assignment import AssignmentOut, AttachmentStartIn, SubmissionIn
from services.assignment import (
    AssignmentNotFoundError,
    AttachmentRejectedError,
    DeadlinePassedError,
    SubmissionNotAllowedError,
)
from services.billing import AccessRequiredError
from services.media import UploadRejectedError

router = APIRouter(tags=["Learning"])

UnitId = Annotated[UUID, Path(description="Identifier of the assignment line.")]

ANSWERS: dict[int | str, dict[str, object]] = {
    401: {"description": "No valid access token."},
    402: {"description": "The course is not open to this account."},
    404: {"description": "No such assignment in a published course."},
}


@router.get("/assignments/{unit_id}", response_model=AssignmentOut, responses={**ANSWERS})
async def get_assignment(
    svc: AssignmentSvc, current_user: CurrentUser, unit_id: UnitId
) -> AssignmentOut:
    """The assignment with every attempt this student has made at it."""
    try:
        return await svc.get_page(unit_id=unit_id, viewer=current_user)
    except AssignmentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="assignment_not_found"
        ) from error
    except AccessRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="access_required"
        ) from error


@router.post(
    "/assignments/{unit_id}/submissions",
    response_model=AssignmentOut,
    responses={
        **ANSWERS,
        409: {"description": "An attempt is already waiting, or the work has been accepted."},
    },
)
async def submit_work(
    svc: AssignmentSvc, current_user: CurrentUser, unit_id: UnitId, payload: SubmissionIn
) -> AssignmentOut:
    """
    Send work in as the next attempt.

    Being late does not stop the work from being accepted into the queue: it is recorded as
    a fact, and what it costs is decided by the person marking it.
    """
    try:
        return await svc.submit(unit_id=unit_id, viewer=current_user, payload=payload)
    except AssignmentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="assignment_not_found"
        ) from error
    except AccessRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="access_required"
        ) from error
    except SubmissionNotAllowedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="submission_already_waiting"
        ) from error
    except DeadlinePassedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="deadline_passed"
        ) from error
    except AttachmentRejectedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="attachment_rejected"
        ) from error


@router.post(
    "/attachments",
    response_model=UploadTicketOut,
    responses={
        401: {"description": "No valid access token."},
        422: {"description": "A file of a kind or size that is refused."},
    },
)
async def start_attachment_upload(
    svc: MediaSvc, current_user: CurrentUser, payload: AttachmentStartIn
) -> UploadTicketOut:
    """
    Reserve a place in storage for a file a student attaches to their work.

    The file goes to storage directly, like every other upload here, and the account that
    reserved the place is written on it: an attachment can only be attached by whoever
    uploaded it.
    """
    try:
        ticket = await svc.start_attachment_upload(
            file_name=payload.file_name,
            size_bytes=payload.size_bytes,
            uploaded_by_id=current_user.id,
        )
    except UploadRejectedError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return UploadTicketOut(
        media_id=ticket.media_id,
        url=ticket.url,
        content_type=ticket.content_type,
        size_bytes=ticket.size_bytes,
    )
