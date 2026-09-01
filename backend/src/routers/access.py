from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from core.access import AdminUser
from core.deps import AccessSvc
from schemas.admin import AccessGrantIn, AccessPageOut
from services.access import GrantNotFoundError, StudentNotFoundError

router = APIRouter(prefix="/admin", tags=["Administration"])

GrantId = Annotated[UUID, Path(description="Identifier of the access grant.")]

FORBIDDEN: dict[int | str, dict[str, object]] = {
    401: {"description": "No valid access token."},
    403: {"description": "Not an admin."},
}


def _missing(detail: str) -> HTTPException:
    """The one answer for anything that is not there."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.get("/access", response_model=AccessPageOut, responses={**FORBIDDEN})
async def list_access(
    svc: AccessSvc,
    admin: AdminUser,
    course_id: Annotated[UUID | None, Query(description="Only grants for this course.")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AccessPageOut:
    """Who has been given access to what, newest first."""
    return await svc.list_grants(course_id=course_id, limit=limit, offset=offset)


@router.post(
    "/access",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**FORBIDDEN, 404: {"description": "No account with this address."}},
)
async def grant_access(svc: AccessSvc, admin: AdminUser, payload: AccessGrantIn) -> None:
    """
    Open a course for a student by hand.

    The account has to exist already: an address that has never signed up is a typo far
    more often than it is a person waiting for access.
    """
    try:
        await svc.grant(
            email=payload.email,
            course_id=payload.course_id,
            granted_by_id=admin.id,
            reason=payload.reason,
        )
    except StudentNotFoundError as error:
        raise _missing("student_not_found") from error


@router.delete(
    "/access/{grant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**FORBIDDEN, 404: {"description": "No such grant."}},
)
async def revoke_access(svc: AccessSvc, admin: AdminUser, grant_id: GrantId) -> None:
    """Close a course again. Everything the student did stays where it is."""
    try:
        await svc.revoke(grant_id)
    except GrantNotFoundError as error:
        raise _missing("grant_not_found") from error
