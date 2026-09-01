"""
Uploading lecture material and handing it back out.

Two rules shape everything here. A file is only real once the storage has confirmed it —
otherwise a broken upload leaves a lecture whose video does not exist, and nobody finds out
until a student opens it. And what a file *is* is decided by its first bytes, not by its
name or by the type the browser announced: both of those are written by whoever uploads.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from core.config import Settings
from core.text import file_extension, slugify
from integrations.storage import StoredObject
from models.base import uuid7
from models.enums import LessonKind, MediaStatus
from models.media_file import MediaFile

GIGABYTE = 1024 * 1024 * 1024
MEGABYTE = 1024 * 1024
# Enough of the head of a file to see what it is. The signatures below all live in the
# first twelve bytes.
SIGNATURE_BYTES = 16
# A lecture longer than a working day is a mistake in the number, not a lecture.
MAX_DURATION_SECONDS = 12 * 60 * 60


class UploadRejectedError(Exception):
    """The file may not be uploaded: wrong kind, wrong size, or not what it claims to be."""


class UploadNotFinishedError(Exception):
    """The storage has no object under this key, so the upload did not finish."""


class MediaNotFoundError(Exception):
    """No such media row."""


@dataclass(frozen=True)
class UploadRule:
    """What one kind of lecture may carry, and how big it may be."""

    content_type: str
    extension: str
    max_bytes: int
    signature: tuple[int, bytes]


# White list, not a black one: a type that is not written down here cannot be uploaded, and
# adding one is a decision somebody makes on purpose. The signature is an offset and the
# bytes expected there — `%PDF` at the start of a PDF, `ftyp` in the second word of an MP4.
RULES: dict[LessonKind, UploadRule] = {
    LessonKind.VIDEO: UploadRule(
        content_type="video/mp4", extension="mp4", max_bytes=2 * GIGABYTE, signature=(4, b"ftyp")
    ),
    LessonKind.PDF: UploadRule(
        content_type="application/pdf",
        extension="pdf",
        max_bytes=50 * MEGABYTE,
        signature=(0, b"%PDF"),
    ),
}


# What a student may attach to a piece of work. Narrower than it looks on purpose: every
# type here is one somebody has to be able to open on the other side.
ATTACHMENT_RULES: tuple[UploadRule, ...] = (
    UploadRule(
        content_type="application/pdf",
        extension="pdf",
        max_bytes=50 * MEGABYTE,
        signature=(0, b"%PDF"),
    ),
    UploadRule(
        content_type="image/png",
        extension="png",
        max_bytes=20 * MEGABYTE,
        signature=(0, b"\x89PNG"),
    ),
    UploadRule(
        content_type="image/jpeg",
        extension="jpg",
        max_bytes=20 * MEGABYTE,
        signature=(0, b"\xff\xd8\xff"),
    ),
    UploadRule(
        content_type="application/zip",
        extension="zip",
        max_bytes=100 * MEGABYTE,
        signature=(0, b"PK\x03\x04"),
    ),
)


@dataclass(frozen=True)
class UploadTicket:
    """Everything the browser needs to put one file into storage itself."""

    media_id: UUID
    url: str
    content_type: str
    size_bytes: int


class Storage(Protocol):
    """
    What this service needs from object storage.

    Named as a protocol rather than taken as the concrete client so a test can hand in a
    storage that answers without a network — the rules being tested here are about sizes
    and signatures, not about HTTP.
    """

    def upload_url(
        self, *, bucket: str, key: str, content_type: str, size_bytes: int, expires_in: int
    ) -> str: ...

    def download_url(self, *, bucket: str, key: str, expires_in: int) -> str: ...

    async def head(self, *, bucket: str, key: str) -> StoredObject | None: ...

    async def first_bytes(self, *, bucket: str, key: str, count: int) -> bytes: ...


class MediaStore(Protocol):
    """What this service needs from the media storage."""

    async def get(self, media_id: UUID) -> MediaFile | None:
        """One media row."""
        ...

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
        """Write down an upload about to start."""
        ...

    async def mark_ready(
        self, media: MediaFile, *, size_bytes: int, duration_seconds: int
    ) -> MediaFile:
        """Record that the object arrived."""
        ...


class Limiter(Protocol):
    """Counts attempts and refuses the ones past the allowance."""

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> None:
        """Register an attempt and raise once the allowance is spent."""
        ...


class MediaService:
    """Issuing upload links, confirming what arrived, and signing playback links."""

    def __init__(
        self,
        *,
        media_repo: MediaStore,
        storage: Storage,
        settings: Settings,
        rate_limiter: Limiter,
    ) -> None:
        self.media_repo = media_repo
        self.storage = storage
        self.settings = settings
        self.rate_limiter = rate_limiter

    async def start_upload(
        self, *, kind: LessonKind, file_name: str, size_bytes: int, uploaded_by_id: UUID
    ) -> UploadTicket:
        """
        Reserve a place in storage and hand back a link that fits this file and no other.

        The size is part of the signature, so the limit holds even if the page is bypassed:
        a larger file arrives with a different length and the storage refuses it. The key is
        ours — the name the file came under is kept for display and never becomes a path.
        """
        rule = RULES.get(kind)
        if rule is None:
            raise UploadRejectedError("unsupported_kind")
        if file_extension(file_name, fallback="") != rule.extension:
            raise UploadRejectedError("unsupported_type")
        return await self._reserve(
            rule=rule,
            scope="lessons",
            file_name=file_name,
            size_bytes=size_bytes,
            uploaded_by_id=uploaded_by_id,
        )

    async def _reserve(
        self,
        *,
        rule: UploadRule,
        scope: str,
        file_name: str,
        size_bytes: int,
        uploaded_by_id: UUID,
    ) -> UploadTicket:
        """
        Write down an upload and sign a link that fits this one file.

        Shared by both kinds of upload, because the dangerous parts are the same for both:
        the size travels inside the signature, and the key is ours.
        """
        if size_bytes <= 0 or size_bytes > rule.max_bytes:
            raise UploadRejectedError("file_too_large")

        # Counted per account, before anything is written: a link that was asked for leaves
        # a row behind whether or not a file ever arrives, and an unbounded loop of asking
        # fills the table with reservations nobody will use.
        await self.rate_limiter.hit(
            f"uploads:{uploaded_by_id}",
            limit=self.settings.upload_tickets_per_account,
            window_seconds=self.settings.upload_window_seconds,
        )

        name = slugify(file_name.rsplit(".", 1)[0], fallback="file")[:60]
        key = f"{scope}/{uuid7()}/{name}.{rule.extension}"
        media = await self.media_repo.create(
            bucket=self.settings.media_bucket_private,
            key=key,
            is_public=False,
            original_name=file_name[:255],
            content_type=rule.content_type,
            size_bytes=size_bytes,
            uploaded_by_id=uploaded_by_id,
        )
        url = self.storage.upload_url(
            bucket=media.bucket,
            key=media.key,
            content_type=rule.content_type,
            size_bytes=size_bytes,
            expires_in=self.settings.upload_link_ttl_seconds,
        )
        return UploadTicket(
            media_id=media.id, url=url, content_type=rule.content_type, size_bytes=size_bytes
        )

    async def start_attachment_upload(
        self, *, file_name: str, size_bytes: int, uploaded_by_id: UUID
    ) -> UploadTicket:
        """
        Reserve a place for a file a student attaches to their work.

        Same shape as a lecture upload and a different white list: work comes as documents,
        photographs of a form or an archive, and never as a video.
        """
        extension = file_extension(file_name, fallback="")
        rule = next((item for item in ATTACHMENT_RULES if item.extension == extension), None)
        if rule is None:
            raise UploadRejectedError("unsupported_type")
        return await self._reserve(
            rule=rule,
            scope="submissions",
            file_name=file_name,
            size_bytes=size_bytes,
            uploaded_by_id=uploaded_by_id,
        )

    async def confirm_upload(self, *, media_id: UUID, duration_seconds: int) -> MediaFile:
        """
        Turn a reserved place into a real file, after asking the storage what is there.

        Three answers have to agree before the material counts as uploaded: the object
        exists, it is the size that was signed for, and its opening bytes are the format it
        claims. Any of them missing leaves the row `pending`, and a lecture with a `pending`
        file shows as having no material rather than as having a broken one.
        """
        media = await self.media_repo.get(media_id)
        if media is None:
            raise MediaNotFoundError(media_id)
        if media.status is MediaStatus.READY:
            return media

        stored = await self.storage.head(bucket=media.bucket, key=media.key)
        if stored is None:
            raise UploadNotFinishedError(media_id)
        self._check_size(media, stored)
        await self._check_signature(media)

        duration = max(0, min(duration_seconds, MAX_DURATION_SECONDS))
        return await self.media_repo.mark_ready(
            media, size_bytes=stored.size_bytes, duration_seconds=duration
        )

    def playback_url(self, media: MediaFile) -> str:
        """
        A link that plays one object and expires.

        The window covers a whole lecture on purpose: a browser re-requests byte ranges of a
        video on the same URL, so a link that dies in five minutes stops the playback in the
        sixth. Honestly: this keeps out strangers, not a student who forwards the link.
        """
        return self.storage.download_url(
            bucket=media.bucket, key=media.key, expires_in=self.settings.playback_link_ttl_seconds
        )

    @staticmethod
    def _check_size(media: MediaFile, stored: StoredObject) -> None:
        """The object must be the size the upload link was signed for."""
        if stored.size_bytes != media.size_bytes:
            raise UploadRejectedError("size_mismatch")

    async def _check_signature(self, media: MediaFile) -> None:
        """The head of the file must match the format it was uploaded as."""
        known = (*RULES.values(), *ATTACHMENT_RULES)
        rule = next((item for item in known if item.content_type == media.content_type), None)
        if rule is None:
            raise UploadRejectedError("unsupported_type")
        offset, expected = rule.signature
        head = await self.storage.first_bytes(
            bucket=media.bucket, key=media.key, count=SIGNATURE_BYTES
        )
        if head[offset : offset + len(expected)] != expected:
            raise UploadRejectedError("unsupported_type")
