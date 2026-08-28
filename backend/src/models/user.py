from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import ActiveMixin, Base, TimeStampMixin, UUIDMixin
from models.enums import UserRole


class User(UUIDMixin, TimeStampMixin, ActiveMixin, Base):
    """A person with an account: student, instructor or administrator."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Empty until the profile screen asks for it: registration takes an address and a
    # password and nothing else.
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=False, length=20),
        default=UserRole.STUDENT,
        nullable=False,
        index=True,
    )
