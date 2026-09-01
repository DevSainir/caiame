from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from core.access import AdminUser
from core.deps import AdministrationSvc, MediaSvc
from schemas.admin import (
    CourseDetailOut,
    CourseIn,
    CourseRowOut,
    CourseStatusIn,
    CourseTreeOut,
    LessonDetailOut,
    LessonIn,
    LessonRowOut,
    MoveIn,
    UnitIn,
    UnitRowOut,
    UnitUpdateIn,
    UploadConfirmIn,
    UploadStartIn,
    UploadTicketOut,
)
from services.administration import (
    CourseInUseError,
    CourseNotFoundForAdminError,
    LessonNotFoundError,
    MaterialNotReadyError,
    ModuleNotEmptyError,
    UnitNotFoundError,
)
from services.media import (
    MediaNotFoundError,
    UploadNotFinishedError,
    UploadRejectedError,
)

router = APIRouter(prefix="/admin", tags=["Administration"])

CourseId = Annotated[UUID, Path(description="Identifier of the course.")]
UnitId = Annotated[UUID, Path(description="Identifier of the programme line.")]
LessonId = Annotated[UUID, Path(description="Identifier of the lecture.")]

# Every route here stands on the admin rung, and every one of them can be handed an
# identifier from another course. Both answers are collected in one place so a new route
# cannot quietly invent a friendlier one.
NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "No such course, line or lecture."}
}
FORBIDDEN: dict[int | str, dict[str, Any]] = {
    401: {"description": "No valid access token."},
    403: {"description": "Not an admin."},
}


def _missing(detail: str) -> HTTPException:
    """The one answer for anything that is not there, or not there for this course."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    """The answer when the request is understood but the state of things refuses it."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


@router.get("/courses", response_model=list[CourseRowOut], responses={**FORBIDDEN})
async def list_courses(svc: AdministrationSvc, admin: AdminUser) -> list[CourseRowOut]:
    """Every course of the academy, drafts included."""
    return await svc.list_courses()


@router.get(
    "/courses/{course_id}", response_model=CourseTreeOut, responses={**FORBIDDEN, **NOT_FOUND}
)
async def get_course(
    svc: AdministrationSvc, admin: AdminUser, course_id: CourseId
) -> CourseTreeOut:
    """The whole programme of one course."""
    try:
        return await svc.get_tree(course_id)
    except CourseNotFoundForAdminError as error:
        raise _missing("course_not_found") from error


@router.put(
    "/courses/{course_id}/status",
    response_model=CourseTreeOut,
    responses={**FORBIDDEN, **NOT_FOUND},
)
async def set_status(
    svc: AdministrationSvc, admin: AdminUser, course_id: CourseId, payload: CourseStatusIn
) -> CourseTreeOut:
    """Publish a course or take it out of the catalogue."""
    try:
        return await svc.set_status(course_id=course_id, status=payload.status)
    except CourseNotFoundForAdminError as error:
        raise _missing("course_not_found") from error


@router.post(
    "/courses/{course_id}/units", response_model=UnitRowOut, responses={**FORBIDDEN, **NOT_FOUND}
)
async def add_unit(
    svc: AdministrationSvc, admin: AdminUser, course_id: CourseId, payload: UnitIn
) -> UnitRowOut:
    """Add a module, an assignment or a test to a course."""
    try:
        return await svc.add_unit(course_id=course_id, payload=payload)
    except CourseNotFoundForAdminError as error:
        raise _missing("course_not_found") from error


@router.put(
    "/courses/{course_id}/units/{unit_id}",
    response_model=UnitRowOut,
    responses={**FORBIDDEN, **NOT_FOUND},
)
async def update_unit(
    svc: AdministrationSvc,
    admin: AdminUser,
    course_id: CourseId,
    unit_id: UnitId,
    payload: UnitUpdateIn,
) -> UnitRowOut:
    """Rename a line of the programme."""
    try:
        return await svc.update_unit(course_id=course_id, unit_id=unit_id, payload=payload)
    except UnitNotFoundError as error:
        raise _missing("unit_not_found") from error


@router.post(
    "/courses/{course_id}/units/{unit_id}/move",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**FORBIDDEN, **NOT_FOUND},
)
async def move_unit(
    svc: AdministrationSvc,
    admin: AdminUser,
    course_id: CourseId,
    unit_id: UnitId,
    payload: MoveIn,
) -> None:
    """Move a line one step up or down."""
    try:
        await svc.move_unit(course_id=course_id, unit_id=unit_id, direction=payload.direction)
    except UnitNotFoundError as error:
        raise _missing("unit_not_found") from error


@router.delete(
    "/courses/{course_id}/units/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **FORBIDDEN,
        **NOT_FOUND,
        409: {"description": "The module still holds lectures."},
    },
)
async def delete_unit(
    svc: AdministrationSvc, admin: AdminUser, course_id: CourseId, unit_id: UnitId
) -> None:
    """Remove an empty line of the programme."""
    try:
        await svc.delete_unit(course_id=course_id, unit_id=unit_id)
    except UnitNotFoundError as error:
        raise _missing("unit_not_found") from error
    except ModuleNotEmptyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="module_not_empty"
        ) from error


@router.post(
    "/courses/{course_id}/units/{unit_id}/lessons",
    response_model=LessonRowOut,
    responses={**FORBIDDEN, **NOT_FOUND},
)
async def add_lesson(
    svc: AdministrationSvc,
    admin: AdminUser,
    course_id: CourseId,
    unit_id: UnitId,
    payload: LessonIn,
) -> LessonRowOut:
    """Add a lecture to a module."""
    try:
        return await svc.add_lesson(course_id=course_id, unit_id=unit_id, payload=payload)
    except UnitNotFoundError as error:
        raise _missing("unit_not_found") from error


@router.put(
    "/courses/{course_id}/lessons/{lesson_id}",
    response_model=LessonRowOut,
    responses={**FORBIDDEN, **NOT_FOUND},
)
async def update_lesson(
    svc: AdministrationSvc,
    admin: AdminUser,
    course_id: CourseId,
    lesson_id: LessonId,
    payload: LessonIn,
) -> LessonRowOut:
    """Change a lecture."""
    try:
        return await svc.update_lesson(course_id=course_id, lesson_id=lesson_id, payload=payload)
    except LessonNotFoundError as error:
        raise _missing("lesson_not_found") from error


@router.post(
    "/courses/{course_id}/lessons/{lesson_id}/move",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**FORBIDDEN, **NOT_FOUND},
)
async def move_lesson(
    svc: AdministrationSvc,
    admin: AdminUser,
    course_id: CourseId,
    lesson_id: LessonId,
    payload: MoveIn,
) -> None:
    """Move a lecture one step inside its module."""
    try:
        await svc.move_lesson(course_id=course_id, lesson_id=lesson_id, direction=payload.direction)
    except LessonNotFoundError as error:
        raise _missing("lesson_not_found") from error


@router.delete(
    "/courses/{course_id}/lessons/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**FORBIDDEN, **NOT_FOUND},
)
async def delete_lesson(
    svc: AdministrationSvc, admin: AdminUser, course_id: CourseId, lesson_id: LessonId
) -> None:
    """Retire a lecture without erasing anybody's history."""
    try:
        await svc.delete_lesson(course_id=course_id, lesson_id=lesson_id)
    except LessonNotFoundError as error:
        raise _missing("lesson_not_found") from error


@router.post(
    "/courses",
    response_model=CourseDetailOut,
    status_code=status.HTTP_201_CREATED,
    responses={**FORBIDDEN},
)
async def create_course(
    svc: AdministrationSvc, admin: AdminUser, payload: CourseIn
) -> CourseDetailOut:
    """Start a new course. It is created as a draft and appears nowhere until published."""
    return await svc.create_course(payload)


@router.get(
    "/courses/{course_id}/card",
    response_model=CourseDetailOut,
    responses={**FORBIDDEN, **NOT_FOUND},
)
async def get_course_card(
    svc: AdministrationSvc, admin: AdminUser, course_id: CourseId
) -> CourseDetailOut:
    """The course itself — title, description, hours, price — as its form shows it."""
    try:
        return await svc.get_course_detail(course_id)
    except CourseNotFoundForAdminError as error:
        raise _missing("course_not_found") from error


@router.put(
    "/courses/{course_id}", response_model=CourseDetailOut, responses={**FORBIDDEN, **NOT_FOUND}
)
async def update_course(
    svc: AdministrationSvc, admin: AdminUser, course_id: CourseId, payload: CourseIn
) -> CourseDetailOut:
    """Change the description of a course. Its address stays as it is."""
    try:
        return await svc.update_course(course_id=course_id, payload=payload)
    except CourseNotFoundForAdminError as error:
        raise _missing("course_not_found") from error


@router.delete(
    "/courses/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **FORBIDDEN,
        **NOT_FOUND,
        409: {"description": "The course is published or has students."},
    },
)
async def delete_course(svc: AdministrationSvc, admin: AdminUser, course_id: CourseId) -> None:
    """Erase a draft nobody is taking; anything else is taken out of the catalogue instead."""
    try:
        await svc.delete_course(course_id)
    except CourseNotFoundForAdminError as error:
        raise _missing("course_not_found") from error
    except CourseInUseError as error:
        raise _conflict("course_in_use") from error


@router.get(
    "/courses/{course_id}/lessons/{lesson_id}",
    response_model=LessonDetailOut,
    responses={**FORBIDDEN, **NOT_FOUND},
)
async def get_lesson(
    svc: AdministrationSvc, admin: AdminUser, course_id: CourseId, lesson_id: LessonId
) -> LessonDetailOut:
    """One lecture with the file behind it."""
    try:
        return await svc.get_lesson_detail(course_id=course_id, lesson_id=lesson_id)
    except LessonNotFoundError as error:
        raise _missing("lesson_not_found") from error


@router.post(
    "/uploads",
    response_model=UploadTicketOut,
    responses={**FORBIDDEN, 422: {"description": "The file is of a kind or size that is refused."}},
)
async def start_upload(svc: MediaSvc, admin: AdminUser, payload: UploadStartIn) -> UploadTicketOut:
    """
    Reserve a place in storage and answer with a link the browser uploads to.

    The file goes to storage directly and never passes through this application: a lecture
    of two gigabytes proxied through a worker occupies it for the whole upload.
    """
    try:
        ticket = await svc.start_upload(
            kind=payload.kind,
            file_name=payload.file_name,
            size_bytes=payload.size_bytes,
            uploaded_by_id=admin.id,
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


@router.post(
    "/courses/{course_id}/lessons/{lesson_id}/material",
    response_model=LessonDetailOut,
    responses={
        **FORBIDDEN,
        **NOT_FOUND,
        409: {"description": "The upload did not finish, or the file is not what it claims."},
    },
)
async def confirm_material(
    svc: AdministrationSvc,
    media_svc: MediaSvc,
    admin: AdminUser,
    course_id: CourseId,
    lesson_id: LessonId,
    payload: UploadConfirmIn,
) -> LessonDetailOut:
    """
    Finish an upload and attach the file to a lecture.

    The storage is asked whether the object is really there and whether it is the size and
    the format it was signed for. Only then does the lecture start pointing at it.
    """
    try:
        await media_svc.confirm_upload(
            media_id=payload.media_id, duration_seconds=payload.duration_seconds
        )
        return await svc.attach_material(
            course_id=course_id, lesson_id=lesson_id, media_id=payload.media_id
        )
    except MediaNotFoundError as error:
        raise _missing("material_not_found") from error
    except LessonNotFoundError as error:
        raise _missing("lesson_not_found") from error
    except (UploadNotFinishedError, UploadRejectedError, MaterialNotReadyError) as error:
        raise _conflict("upload_not_finished") from error
