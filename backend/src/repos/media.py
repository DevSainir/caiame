from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import MediaStatus
from models.media_file import MediaFile


class MediaRepo:
    """Data access for the rows that describe objects in storage."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, media_id: UUID) -> MediaFile | None:
        """One media row by its id, whatever state it is in."""
        media: MediaFile | None = await self.session.get(MediaFile, media_id)
        return media

    async def create(
        self,
        *,
        bucket: str,
        key: str,
        is_public: bool,
        original_name: str,
        content_type: str,
        size_bytes: int,
        uploaded_by_id: UUID | None,
    ) -> MediaFile:
        """
        Write down an upload that is about to start.

        The row is born `pending`: the link has been issued, but nothing has arrived yet.
        """
        media = MediaFile(
            bucket=bucket,
            key=key,
            is_public=is_public,
            original_name=original_name,
            content_type=content_type,
            size_bytes=size_bytes,
            status=MediaStatus.PENDING,
            uploaded_by_id=uploaded_by_id,
        )
        self.session.add(media)
        await self.session.flush()
        return media

    async def mark_ready(
        self, media: MediaFile, *, size_bytes: int, duration_seconds: int
    ) -> MediaFile:
        """Record that the object is really in storage, at the size the storage reports."""
        media.size_bytes = size_bytes
        media.duration_seconds = duration_seconds
        media.status = MediaStatus.READY
        await self.session.flush()
        return media

    async def list_pending_for(self, uploader_id: UUID) -> list[MediaFile]:
        """Uploads this account started and never finished. Used by nothing but housekeeping."""
        rows = await self.session.scalars(
            select(MediaFile).where(
                MediaFile.uploaded_by_id == uploader_id, MediaFile.status == MediaStatus.PENDING
            )
        )
        return list(rows.all())
