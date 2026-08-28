from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimeStampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.user import User


class RefreshToken(UUIDMixin, TimeStampMixin, Base):
    """
    One issued refresh token.

    Rotation means every refresh writes a new row and revokes the old one. `family_id`
    ties the whole chain back to the login it started from, which is what makes a replay
    actionable: presenting an already-revoked token can only mean it leaked, and the
    answer is to kill the family rather than the single row.

    The column holds a hash. A stolen database dump must not be a set of working sessions.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    family_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(lazy="raise")
