from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import UserRole
from models.user import User


class UserRepo:
    """Data access for user accounts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        """Look an account up by address. Comparison is case-insensitive by storage convention."""
        user: User | None = await self.session.scalar(
            select(User).where(User.email == email.lower())
        )
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Look an account up by id, used when a refresh token names its owner."""
        user: User | None = await self.session.get(User, user_id)
        return user

    async def update_full_name(self, user: User, *, full_name: str) -> User:
        """Store a new display name and flush, so the caller reads back what was written."""
        user.full_name = full_name
        await self.session.flush()
        return user

    async def create(
        self, *, email: str, password_hash: str, full_name: str, role: UserRole
    ) -> User:
        """Insert an account and flush, so the generated id is available to the caller."""
        user = User(
            email=email.lower(), password_hash=password_hash, full_name=full_name, role=role
        )
        self.session.add(user)
        await self.session.flush()
        return user
