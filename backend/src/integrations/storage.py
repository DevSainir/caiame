"""
S3-compatible storage, spoken to directly instead of through a vendor SDK.

Everything needed here is a signature: a link the browser uploads to, a link the player
reads from, and the same mechanism for the few requests the application makes itself.
Signing is arithmetic over the request — no network and no dependency — so an SDK would
only add weight to the image and a second way to configure the same four values.

The file never passes through the application. A two-gigabyte lecture proxied through a
worker holds that worker for the whole upload and runs into every proxy limit on the way;
direct upload is not an optimisation here but the only shape that works.
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

import httpx

from core.config import Settings

ALGORITHM = "AWS4-HMAC-SHA256"
# Presigned requests are signed without knowing the body, which is what the browser is
# about to stream. The size is pinned through a signed Content-Length header instead.
UNSIGNED_PAYLOAD = "UNSIGNED-PAYLOAD"


@dataclass(frozen=True)
class StoredObject:
    """What the storage says about an object that is really there."""

    size_bytes: int
    content_type: str


def _sign(key: bytes, message: str) -> bytes:
    """One HMAC-SHA256 round of the signing key derivation."""
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _encode_path(path: str) -> str:
    """Percent-encode an object path, leaving the separators between segments alone."""
    return quote(path, safe="/~")


class ObjectStorage:
    """Signed access to one S3-compatible endpoint, path-style."""

    def __init__(self, settings: Settings) -> None:
        self.endpoint = settings.media_endpoint.rstrip("/")
        self.region = settings.media_region
        self.access_key = settings.media_access_key
        self.secret_key = settings.media_secret_key

    def presigned_url(
        self,
        *,
        method: str,
        bucket: str,
        key: str,
        expires_in: int,
        signed_headers: dict[str, str] | None = None,
    ) -> str:
        """
        A URL that carries its own authorisation for one method, one object and one window.

        Headers passed here are part of the signature: the storage refuses the request if
        the browser sends anything else. That is how the size limit is enforced — a file
        larger than the one we signed for arrives with a different Content-Length and the
        signature stops matching. A limit checked only in the page is not a limit.
        """
        now = datetime.now(UTC)
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        date = now.strftime("%Y%m%d")
        scope = f"{date}/{self.region}/s3/aws4_request"

        host = self.endpoint.split("://", 1)[1]
        headers = {
            "host": host,
            **{name.lower(): value for name, value in (signed_headers or {}).items()},
        }
        signed = ";".join(sorted(headers))
        canonical_headers = "".join(f"{name}:{headers[name]}\n" for name in sorted(headers))

        query = {
            "X-Amz-Algorithm": ALGORITHM,
            "X-Amz-Credential": f"{self.access_key}/{scope}",
            "X-Amz-Date": stamp,
            "X-Amz-Expires": str(expires_in),
            "X-Amz-SignedHeaders": signed,
        }
        canonical_query = "&".join(
            f"{quote(name, safe='')}={quote(query[name], safe='-_.~')}" for name in sorted(query)
        )

        path = _encode_path(f"/{bucket}/{key}")
        canonical_request = "\n".join(
            [method, path, canonical_query, canonical_headers, signed, UNSIGNED_PAYLOAD]
        )
        to_sign = "\n".join(
            [
                ALGORITHM,
                stamp,
                scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )

        signing_key = _sign(f"AWS4{self.secret_key}".encode(), date)
        for part in (self.region, "s3", "aws4_request"):
            signing_key = _sign(signing_key, part)
        signature = hmac.new(signing_key, to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        return f"{self.endpoint}{path}?{canonical_query}&X-Amz-Signature={signature}"

    def upload_url(
        self, *, bucket: str, key: str, content_type: str, size_bytes: int, expires_in: int
    ) -> str:
        """A link the browser may PUT exactly this file to, and nothing else."""
        return self.presigned_url(
            method="PUT",
            bucket=bucket,
            key=key,
            expires_in=expires_in,
            signed_headers={"content-type": content_type, "content-length": str(size_bytes)},
        )

    def download_url(self, *, bucket: str, key: str, expires_in: int) -> str:
        """A link that plays or downloads one object until it expires."""
        return self.presigned_url(method="GET", bucket=bucket, key=key, expires_in=expires_in)

    async def head(self, *, bucket: str, key: str, expires_in: int = 60) -> StoredObject | None:
        """
        What the storage holds under this key, or nothing if the upload never landed.

        Asked before an upload is called finished. Without it the catalogue fills with
        lectures whose video does not exist: the link was issued, the upload broke halfway,
        and nobody noticed until a student opened the lesson.
        """
        url = self.presigned_url(method="HEAD", bucket=bucket, key=key, expires_in=expires_in)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.head(url)
        if response.status_code != httpx.codes.OK:
            return None
        return StoredObject(
            size_bytes=int(response.headers.get("content-length", 0)),
            content_type=response.headers.get("content-type", ""),
        )

    async def first_bytes(self, *, bucket: str, key: str, count: int) -> bytes:
        """
        The opening bytes of an object, for checking what it actually is.

        The extension and the Content-Type both come from whoever uploaded the file, so
        neither answers the question. The signature at the start of the file does.
        """
        url = self.presigned_url(method="GET", bucket=bucket, key=key, expires_in=60)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers={"Range": f"bytes=0-{count - 1}"})
        if response.status_code not in (httpx.codes.OK, httpx.codes.PARTIAL_CONTENT):
            return b""
        return response.content[:count]

    async def remove(self, *, bucket: str, key: str) -> None:
        """
        Delete one object, best effort.

        Called when a lecture's file is replaced. A failure here leaves an object nobody
        points at, which costs storage and nothing else — so it must not fail the request
        that replaced the file.
        """
        url = self.presigned_url(method="DELETE", bucket=bucket, key=key, expires_in=60)
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(url)
