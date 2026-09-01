from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin
from models.enums import AccessSource


class Entitlement(UUIDMixin, TimeStampMixin, Base):
    """
    The right to open one course — or the whole catalogue, when `course_id` is empty.

    A payment is an event; the right is a state. They are kept apart because they come
    apart constantly: a right exists without a payment (granted by hand, a promotion) and a
    payment exists without a right (after a refund). Only `services/billing.py` reads this
    table.

    Withdrawing a right is `revoked_at`, never a delete: a deleted row cannot answer
    «did this person have access in March», which is the question every dispute asks.
    """

    __tablename__ = "entitlements"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source: Mapped[AccessSource] = mapped_column(
        SAEnum(AccessSource, name="access_source", native_enum=False, length=20), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Open-ended by default. A course bought once does not expire; a subscription will fill
    # this in from the paid period when payments arrive.
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Who granted it and why. A right with nobody's name on it cannot be investigated.
    granted_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(300), nullable=False, default="")
