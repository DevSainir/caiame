from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import ActiveMixin, Base, TimeStampMixin, UUIDMixin


class Specialization(UUIDMixin, TimeStampMixin, ActiveMixin, Base):
    """A medical field a course belongs to — cardiology, neurology and so on."""

    __tablename__ = "specializations"

    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
