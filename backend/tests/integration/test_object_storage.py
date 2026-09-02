"""
The signatures against a real S3-compatible storage.

Signing is arithmetic, and arithmetic that is only checked against itself always agrees.
What matters here is the answer of the other side: whether the storage accepts the link we
issue, and — the part the whole size limit rests on — whether it refuses everything else.

Locally the other side is the MinIO of `docker-compose`; in production the same code talks
to R2. The suite skips itself when no storage is listening.
"""

import httpx
import pytest

from core.config import get_settings
from integrations.storage import ObjectStorage

# A tiny MP4 header: enough for a magic-byte check to have something to read.
CONTENT = bytes.fromhex("00000018667479706d70343200000000") + b"\x00" * 512
CONTENT_TYPE = "video/mp4"


@pytest.fixture
async def storage() -> ObjectStorage:
    """Storage with a bucket to write into, or a skip when nothing is listening."""
    settings = get_settings()
    client = ObjectStorage(settings)
    try:
        async with httpx.AsyncClient(timeout=2) as probe:
            await probe.get(f"{settings.media_endpoint}/minio/health/live")
    except Exception as error:  # any connection failure means "no storage"
        pytest.skip(f"Object storage is unavailable: {error}")
    return client


@pytest.fixture
def bucket() -> str:
    """The private bucket, the one every lecture file lands in."""
    return get_settings().media_bucket_private


async def _put(url: str, *, content: bytes, headers: dict[str, str]) -> int:
    """A raw upload, the way a browser would make it."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.put(url, content=content, headers=headers)
    return response.status_code


async def test_the_link_we_issue_is_accepted_and_the_object_lands(
    storage: ObjectStorage, bucket: str
) -> None:
    """The whole upload path in one go: sign, upload, ask the storage what it holds."""
    key = "tests/upload-accepted.mp4"
    url = storage.upload_url(
        bucket=bucket,
        key=key,
        content_type=CONTENT_TYPE,
        size_bytes=len(CONTENT),
        expires_in=300,
    )

    status = await _put(
        url,
        content=CONTENT,
        headers={"content-type": CONTENT_TYPE, "content-length": str(len(CONTENT))},
    )

    assert status == httpx.codes.OK
    stored = await storage.head(bucket=bucket, key=key)
    assert stored is not None
    assert stored.size_bytes == len(CONTENT)
    assert stored.content_type == CONTENT_TYPE
    await storage.remove(bucket=bucket, key=key)


async def test_a_file_of_another_size_does_not_fit_the_signature(
    storage: ObjectStorage, bucket: str
) -> None:
    """
    This is the size limit, and it lives here rather than in the page.

    The page can be bypassed; the signature cannot. A link signed for one length does not
    accept a longer body, so «up to two gigabytes» stays true for a request nobody made
    through our interface.
    """
    key = "tests/upload-too-big.mp4"
    url = storage.upload_url(
        bucket=bucket, key=key, content_type=CONTENT_TYPE, size_bytes=len(CONTENT), expires_in=300
    )
    bigger = CONTENT + b"\x00" * 1024

    status = await _put(
        url,
        content=bigger,
        headers={"content-type": CONTENT_TYPE, "content-length": str(len(bigger))},
    )

    assert status >= httpx.codes.BAD_REQUEST
    assert await storage.head(bucket=bucket, key=key) is None


async def test_a_file_of_another_type_does_not_fit_the_signature(
    storage: ObjectStorage, bucket: str
) -> None:
    """The type is signed for the same reason: what was agreed is what may be sent."""
    key = "tests/upload-wrong-type.mp4"
    url = storage.upload_url(
        bucket=bucket, key=key, content_type=CONTENT_TYPE, size_bytes=len(CONTENT), expires_in=300
    )

    status = await _put(
        url,
        content=CONTENT,
        headers={"content-type": "application/pdf", "content-length": str(len(CONTENT))},
    )

    assert status >= httpx.codes.BAD_REQUEST


async def test_an_unsigned_request_is_refused(storage: ObjectStorage, bucket: str) -> None:
    """The bucket is private: without a signature there is no way in at all."""
    settings = get_settings()

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.put(
            f"{settings.media_endpoint}/{bucket}/tests/unsigned.mp4", content=CONTENT
        )

    assert response.status_code >= httpx.codes.BAD_REQUEST


async def test_the_reading_link_returns_the_file_and_its_opening_bytes(
    storage: ObjectStorage, bucket: str
) -> None:
    """
    What a student's player gets, and what the confirmation step reads.

    The opening bytes are the only honest answer to «what is this file»: the extension and
    the declared type both come from whoever uploaded it.
    """
    key = "tests/download.mp4"
    url = storage.upload_url(
        bucket=bucket, key=key, content_type=CONTENT_TYPE, size_bytes=len(CONTENT), expires_in=300
    )
    await _put(
        url,
        content=CONTENT,
        headers={"content-type": CONTENT_TYPE, "content-length": str(len(CONTENT))},
    )

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(storage.download_url(bucket=bucket, key=key, expires_in=300))
    head = await storage.first_bytes(bucket=bucket, key=key, count=12)

    assert response.status_code == httpx.codes.OK
    assert response.content == CONTENT
    assert head[4:8] == b"ftyp"
    await storage.remove(bucket=bucket, key=key)


async def test_a_removed_object_is_gone(storage: ObjectStorage, bucket: str) -> None:
    """Replacing a lecture file deletes the old one; a failure here fills the bucket."""
    key = "tests/removed.mp4"
    url = storage.upload_url(
        bucket=bucket, key=key, content_type=CONTENT_TYPE, size_bytes=len(CONTENT), expires_in=300
    )
    await _put(
        url,
        content=CONTENT,
        headers={"content-type": CONTENT_TYPE, "content-length": str(len(CONTENT))},
    )

    await storage.remove(bucket=bucket, key=key)

    assert await storage.head(bucket=bucket, key=key) is None
