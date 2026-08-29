from typing import Protocol

from models.user import User
from schemas.user import UserOut


class UserWriter(Protocol):
    """What the profile screen needs from user storage."""

    async def update_full_name(self, user: User, *, full_name: str) -> User:
        """Store a new display name."""
        ...


class UserService:
    """Application rules for a person's own account."""

    def __init__(self, *, user_repo: UserWriter) -> None:
        self.user_repo = user_repo

    async def update_profile(self, *, user: User, full_name: str) -> UserOut:
        """
        Change the display name of the account making the request.

        The account comes from the access token rather than the payload: an endpoint that
        takes a user id is an endpoint that edits other people's profiles.
        """
        updated = await self.user_repo.update_full_name(user, full_name=full_name)
        return UserOut.model_validate(updated)
