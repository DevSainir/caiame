from fastapi import APIRouter

from core.deps import CurrentUser, EnrollmentSvc, UserSvc
from schemas.enrollment import MyCourseOut
from schemas.user import UserOut, UserUpdateIn

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch(
    "/me",
    response_model=UserOut,
    responses={
        200: {"description": "Profile updated."},
        401: {"description": "No valid access token."},
        422: {"description": "An empty name, or one longer than 200 characters."},
    },
)
async def update_me(payload: UserUpdateIn, current_user: CurrentUser, svc: UserSvc) -> UserOut:
    """Change the display name of the signed-in account."""
    return await svc.update_profile(user=current_user, full_name=payload.full_name)


@router.get(
    "/me/courses",
    response_model=list[MyCourseOut],
    responses={
        200: {"description": "Courses this student has started."},
        401: {"description": "No valid access token."},
    },
)
async def my_courses(current_user: CurrentUser, svc: EnrollmentSvc) -> list[MyCourseOut]:
    """
    The signed-in student's own courses, with the progress counted right now.

    Only their own: the account comes from the token, and there is no identifier in the
    path to point at somebody else's studying.
    """
    return await svc.my_courses(viewer=current_user)
