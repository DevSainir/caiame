from sqlalchemy import Enum as SAEnum
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import ActiveMixin, Base, TimeStampMixin, UUIDMixin
from models.enums import Audience


class Specialization(UUIDMixin, TimeStampMixin, ActiveMixin, Base):
    """A field a course belongs to — ophthalmology, therapy and so on."""

    __tablename__ = "specializations"

    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    audience: Mapped[Audience] = mapped_column(
        SAEnum(Audience, name="audience", native_enum=False, length=20),
        default=Audience.DOCTOR,
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
