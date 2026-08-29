"""Cloudflare R2 access over the S3 protocol."""

from pathlib import Path

import boto3
from botocore.config import Config
from config import Settings

DAILY = "daily/"
WEEKLY = "weekly/"
MONTHLY = "monthly/"


def make_client(settings: Settings):  # type: ignore[no-untyped-def]
    """An S3 client pointed at the R2 endpoint."""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", retries={"max_attempts": 5, "mode": "standard"}),
    )


def upload(client, bucket: str, path: Path, key: str) -> None:  # type: ignore[no-untyped-def]
    """Store a file under the given key."""
    client.upload_file(str(path), bucket, key)


def copy_within_bucket(  # type: ignore[no-untyped-def]
    client, bucket: str, source_key: str, target_key: str
) -> None:
    """
    Copy an object inside the bucket, letting the storage do the work.

    The weekly and monthly copies are the very archive that already went to daily/. Copying
    server-side spends no outbound bandwidth and guarantees all three objects are identical
    byte for byte.
    """
    client.copy_object(
        Bucket=bucket, Key=target_key, CopySource={"Bucket": bucket, "Key": source_key}
    )


def download(client, bucket: str, key: str, target: Path) -> None:  # type: ignore[no-untyped-def]
    """Fetch an object back — this is what proves the stored copy is readable."""
    client.download_file(bucket, key, str(target))
