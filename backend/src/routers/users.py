from fastapi import APIRouter

from core.deps import CurrentUser, UserSvc
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
