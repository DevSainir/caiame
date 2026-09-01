from uuid import UUID

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimeStampMixin, UUIDMixin
from models.enums import MediaStatus


class MediaFile(UUIDMixin, TimeStampMixin, Base):
    """
    One object in storage: a lecture video, a lecture handout, a course cover.

    A lesson points at this row and not at a URL, because the URL of a private object is
    signed and short-lived — it is an answer to «show it to this person now», not an
    address. Moving to another storage changes the columns here and nothing else.

    The name the file arrived under is kept for display only. It never becomes part of the
    key: a name is user input, and user input in a path is how `../` and look-alike
    characters become somebody's problem.
    """

    __tablename__ = "media_files"

    bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # Read from the file by the browser that uploaded it — an administrator's browser,
    # which has the whole file in hand. A student's player is never asked: there the number
    # decides whether a lesson counts as watched.
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[MediaStatus] = mapped_column(
        SAEnum(MediaStatus, name="media_status", native_enum=False, length=20),
        default=MediaStatus.PENDING,
        nullable=False,
        index=True,
    )
    uploaded_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
