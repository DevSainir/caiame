from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from core.access import AdminUser
from core.deps import AdministrationSvc
from schemas.admin import (
    CourseRowOut,
    CourseStatusIn,
    CourseTreeOut,
    LessonIn,
    LessonRowOut,
    MoveIn,
    UnitIn,
    UnitRowOut,
    UnitUpdateIn,
)
from services.administration import (
    CourseNotFoundForAdminError,
    LessonNotFoundError,
    ModuleNotEmptyError,
    UnitNotFoundError,
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
