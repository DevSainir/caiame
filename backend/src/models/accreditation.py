from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import ActiveMixin, Base, TimeStampMixin, UUIDMixin


class Accreditation(UUIDMixin, TimeStampMixin, ActiveMixin, Base):
    """
    A credit scheme a course is accredited under.

    Kept as a table rather than an enum: the list of schemes is set by regulators and
    changes without a deploy, and each one carries its own short code for certificates.
    """

    __tablename__ = "accreditations"

    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    short_code: Mapped[str] = mapped_column(String(20), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
