"""
Uploading a lecture: what is refused, and what counts as arrived.

The rules being checked here are the ones that hold when the page is bypassed — a size, a
white list and the first bytes of the file — so the storage is a stand-in and no request
leaves the process.
"""

import pytest

from core.config import Settings
from integrations.storage import StoredObject
from models.base import uuid7
from models.enums import LessonKind, MediaStatus
from services.media import (
    GIGABYTE,
    MEGABYTE,
    MediaService,
    UploadNotFinishedError,
    UploadRejectedError,
)
from services.rate_limit import RateLimitExceededError, RateLimitService
from tests.support.fakes import FakeCounterStore, FakeMediaRepo

MP4_HEAD = b"\x00\x00\x00\x18ftypmp42"
PDF_HEAD = b"%PDF-1.7 head..."


class FakeStorage:
    """Storage that answers from memory: what is in it, and what its objects start with."""

    def __init__(self, *, stored: StoredObject | None = None, head_bytes: bytes = b"") -> None:
        self.stored = stored
        self.head_bytes = head_bytes
        self.signed: list[tuple[str, int]] = []

    def upload_url(
        self, *, bucket: str, key: str, content_type: str, size_bytes: int, expires_in: int
    ) -> str:
        """Remember what was signed, so a test can check the size travelled with it."""
        self.signed.append((content_type, size_bytes))
        return f"https://storage.example/{bucket}/{key}?signed"

    def download_url(self, *, bucket: str, key: str, expires_in: int) -> str:
        """A link that would play the object."""
        return f"https://storage.example/{bucket}/{key}?playback"

    async def head(self, *, bucket: str, key: str) -> StoredObject | None:
        """What the storage holds, or nothing."""
        return self.stored

    async def first_bytes(self, *, bucket: str, key: str, count: int) -> bytes:
        """The opening bytes of the object."""
        return self.head_bytes[:count]


def _service(storage: FakeStorage, repo: FakeMediaRepo | None = None) -> MediaService:
    """The media service over a storage that answers from memory."""
    return MediaService(
        media_repo=repo or FakeMediaRepo(),
        storage=storage,
        settings=Settings(),
        rate_limiter=RateLimitService(store=FakeCounterStore()),
    )


async def test_a_video_over_the_limit_is_refused() -> None:
    """The limit is the point of the whole ticket: three gigabytes never gets a link."""
    service = _service(FakeStorage())

    with pytest.raises(UploadRejectedError):
        await service.start_upload(
            kind=LessonKind.VIDEO,
            file_name="lecture.mp4",
            size_bytes=3 * GIGABYTE,
            uploaded_by_id=uuid7(),
        )


async def test_a_file_of_the_wrong_kind_is_refused() -> None:
    """The list of what may be uploaded is white: an archive is not on it."""
    service = _service(FakeStorage())

    with pytest.raises(UploadRejectedError):
        await service.start_upload(
            kind=LessonKind.VIDEO,
            file_name="lecture.zip",
            size_bytes=MEGABYTE,
            uploaded_by_id=uuid7(),
        )


async def test_the_size_is_signed_into_the_link() -> None:
    """
    A limit that lives only in the page is not a limit.

    The signature covers the length, so a larger file arrives with a different one and the
    storage refuses it without asking us.
    """
    storage = FakeStorage()
    service = _service(storage)

    await service.start_upload(
        kind=LessonKind.VIDEO,
        file_name="lecture.mp4",
        size_bytes=10 * MEGABYTE,
        uploaded_by_id=uuid7(),
    )

    assert storage.signed == [("video/mp4", 10 * MEGABYTE)]


async def test_the_uploaded_name_never_becomes_the_path() -> None:
    """A name is user input, and user input in a path is somebody else's directory."""
    repo = FakeMediaRepo()
    service = _service(FakeStorage(), repo)

    await service.start_upload(
        kind=LessonKind.PDF,
        file_name="../../etc/passwd.pdf",
        size_bytes=MEGABYTE,
        uploaded_by_id=uuid7(),
    )

    key = repo.files[0].key
    assert ".." not in key
    assert key.startswith("lessons/")
    assert repo.files[0].original_name == "../../etc/passwd.pdf"


async def test_a_broken_upload_leaves_the_file_unfinished() -> None:
    """
    Nothing in storage means nothing was uploaded.

    Without this the catalogue fills with lectures whose video does not exist: the link was
    issued, the upload broke, and nobody found out until a student opened the lesson.
    """
    repo = FakeMediaRepo()
    service = _service(FakeStorage(stored=None), repo)
    ticket = await service.start_upload(
        kind=LessonKind.VIDEO,
        file_name="lecture.mp4",
        size_bytes=MEGABYTE,
        uploaded_by_id=uuid7(),
    )

    with pytest.raises(UploadNotFinishedError):
        await service.confirm_upload(media_id=ticket.media_id, duration_seconds=60)

    assert repo.files[0].status is MediaStatus.PENDING


async def test_a_file_that_is_not_what_it_claims_is_refused() -> None:
    """The extension and the announced type are both written by whoever uploads."""
    repo = FakeMediaRepo()
    storage = FakeStorage(
        stored=StoredObject(size_bytes=MEGABYTE, content_type="video/mp4"), head_bytes=PDF_HEAD
    )
    service = _service(storage, repo)
    ticket = await service.start_upload(
        kind=LessonKind.VIDEO,
        file_name="lecture.mp4",
        size_bytes=MEGABYTE,
        uploaded_by_id=uuid7(),
    )

    with pytest.raises(UploadRejectedError):
        await service.confirm_upload(media_id=ticket.media_id, duration_seconds=60)

    assert repo.files[0].status is MediaStatus.PENDING


async def test_a_file_of_another_size_than_signed_is_refused() -> None:
    """The object in storage has to be the one the link was issued for."""
    repo = FakeMediaRepo()
    storage = FakeStorage(
        stored=StoredObject(size_bytes=5 * MEGABYTE, content_type="video/mp4"),
        head_bytes=MP4_HEAD,
    )
    service = _service(storage, repo)
    ticket = await service.start_upload(
        kind=LessonKind.VIDEO,
        file_name="lecture.mp4",
        size_bytes=MEGABYTE,
        uploaded_by_id=uuid7(),
    )

    with pytest.raises(UploadRejectedError):
        await service.confirm_upload(media_id=ticket.media_id, duration_seconds=60)


async def test_a_real_upload_becomes_ready() -> None:
    """The straight path: the object is there, the right size, and starts as an MP4 does."""
    repo = FakeMediaRepo()
    storage = FakeStorage(
        stored=StoredObject(size_bytes=MEGABYTE, content_type="video/mp4"), head_bytes=MP4_HEAD
    )
    service = _service(storage, repo)
    ticket = await service.start_upload(
        kind=LessonKind.VIDEO,
        file_name="lecture.mp4",
        size_bytes=MEGABYTE,
        uploaded_by_id=uuid7(),
    )

    media = await service.confirm_upload(media_id=ticket.media_id, duration_seconds=1380)

    assert media.status is MediaStatus.READY
    assert media.duration_seconds == 1380


async def test_an_absurd_length_is_capped_rather_than_believed() -> None:
    """The length comes from a browser, so it is bounded before it is stored."""
    repo = FakeMediaRepo()
    storage = FakeStorage(
        stored=StoredObject(size_bytes=MEGABYTE, content_type="application/pdf"),
        head_bytes=PDF_HEAD,
    )
    service = _service(storage, repo)
    ticket = await service.start_upload(
        kind=LessonKind.PDF,
        file_name="handout.pdf",
        size_bytes=MEGABYTE,
        uploaded_by_id=uuid7(),
    )

    media = await service.confirm_upload(media_id=ticket.media_id, duration_seconds=10**9)

    assert media.duration_seconds == 12 * 60 * 60


async def test_asking_for_links_without_end_is_refused() -> None:
    """
    Every issued link leaves a row behind, whether or not a file follows it.

    Without a count, a loop asking for links fills the table with reservations nobody will
    ever use — and it costs the person doing it nothing.
    """
    repo = FakeMediaRepo()
    service = MediaService(
        media_repo=repo,
        storage=FakeStorage(),
        settings=Settings(),
        rate_limiter=RateLimitService(store=FakeCounterStore()),
    )
    uploader = uuid7()

    for _ in range(Settings().upload_tickets_per_account):
        await service.start_upload(
            kind=LessonKind.PDF,
            file_name="handout.pdf",
            size_bytes=MEGABYTE,
            uploaded_by_id=uploader,
        )

    with pytest.raises(RateLimitExceededError):
        await service.start_upload(
            kind=LessonKind.PDF,
            file_name="handout.pdf",
            size_bytes=MEGABYTE,
            uploaded_by_id=uploader,
        )


async def test_the_count_is_kept_per_account() -> None:
    """One person filling a course must not lock out everybody else."""
    limiter = RateLimitService(store=FakeCounterStore())
    service = MediaService(
        media_repo=FakeMediaRepo(),
        storage=FakeStorage(),
        settings=Settings(),
        rate_limiter=limiter,
    )
    busy = uuid7()
    for _ in range(Settings().upload_tickets_per_account):
        await service.start_upload(
            kind=LessonKind.PDF, file_name="a.pdf", size_bytes=MEGABYTE, uploaded_by_id=busy
        )

    ticket = await service.start_upload(
        kind=LessonKind.PDF, file_name="b.pdf", size_bytes=MEGABYTE, uploaded_by_id=uuid7()
    )

    assert ticket.url
