import secrets
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uuid7() -> UUID:
    """
    Time-ordered UUID (RFC 9562, version 7).

    Ordered by time, so inserts land on the hot leaf pages of the B-tree instead of
    scattering; random in the low bits, so an id in a URL is not an enumerator of
    someone else's records the way a serial integer is.
    """
    milliseconds = int(time.time() * 1000)
    value = (milliseconds & 0xFFFFFFFFFFFF) << 80
    value |= 0x7 << 76
    value |= secrets.randbits(12) << 64
    value |= 0b10 << 62
    value |= secrets.randbits(62)
    return UUID(int=value)


class Base(DeclarativeBase):
    """Declarative base for every model in the single `public` schema."""


class UUIDMixin:
    """Primary key column shared by every table."""

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)


class TimeStampMixin:
    """Creation and update timestamps, always in UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ActiveMixin:
    """Soft on/off switch for rows that must not disappear from other tables' history."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
