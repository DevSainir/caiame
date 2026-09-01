from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_token import RefreshToken


class RefreshTokenRepo:
    """Data access for issued refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Find an issued token by its stored hash."""
        token: RefreshToken | None = await self.session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return token

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        family_id: UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        """Store a newly issued token and flush, so its id is available to the caller."""
        token = RefreshToken(
            user_id=user_id, token_hash=token_hash, family_id=family_id, expires_at=expires_at
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def revoke(self, token: RefreshToken, *, at: datetime) -> None:
        """Mark one token as spent."""
        token.revoked_at = at
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: UUID, *, at: datetime) -> int:
        """
        End every live session of one account and say how many were ended.

        Called when the password changes. A refresh token outlives the password it was
        issued under, so without this a stolen session survives the very action taken to
        stop it.
        """
        live = (
            await self.session.scalars(
                select(RefreshToken).where(
                    RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
                )
            )
        ).all()
        for token in live:
            token.revoked_at = at
        await self.session.flush()
        return len(live)

    async def revoke_family(self, family_id: UUID, *, at: datetime) -> None:
        """
        Revoke every live token of one login chain.

        Called when a revoked token is presented again: that can only happen if a token
        leaked, and the safe answer is to end every session descended from that login.
        """
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=at)
        )
        await self.session.flush()
