#!/usr/bin/env python3
"""
Restore from a backup.

A tool for the day it is needed, so by default it touches nothing: it downloads the
archive, decrypts it, lays the files out and prints what to do next. Restoring into a
database takes an explicit `--into`, because restoring over a live database erases what
is in it right now.
"""

import argparse
import subprocess
import sys
import tarfile
from pathlib import Path

from config import Settings
from crypto import decrypt
from storage import DAILY, download, make_client


def main() -> int:
    """Download the chosen archive, unpack it and, if asked, restore it into a database."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", help="object key in the bucket; defaults to the newest in daily/")
    parser.add_argument("--list", action="store_true", help="list available copies and exit")
    parser.add_argument("--out", default="/tmp/caiame-restore", help="where to unpack")
    parser.add_argument(
        "--into",
        help="database to restore into. WITHOUT THIS FLAG NOTHING IS CHANGED",
    )
    options = parser.parse_args()

    settings = Settings.from_environment()
    client = make_client(settings)

    if options.list:
        for prefix in (DAILY, "weekly/", "monthly/"):
            keys = list_backups(client, settings.s3_bucket, prefix)
            print(f"\n{prefix}  ({len(keys)})")
            for key, size, modified in keys[-10:]:
                print(f"  {modified:%Y-%m-%d %H:%M}  {size / 1024:8.0f} KB  {key}")
        return 0

    key = options.key or latest_key(client, settings.s3_bucket)
    if not key:
        print("the bucket holds no copies", file=sys.stderr)
        return 1

    out = Path(options.out)
    out.mkdir(parents=True, exist_ok=True)
    encrypted = out / "backup.tar.age"
    archive = out / "backup.tar"

    print(f"downloading {key}")
    download(client, settings.s3_bucket, key, encrypted)
    decrypt(encrypted, archive, settings.identity_path(out))
    with tarfile.open(archive) as tar:
        tar.extractall(out, filter="data")
    print(f"unpacked into {out}: db.dump and env")

    if not options.into:
        print(
            "\nThe database was not touched. To restore, run again with --into <database>.\n"
            f"The server secrets are in {out / 'env'} — check them before starting the app."
        )
        return 0

    return restore_into(settings, out / "db.dump", options.into)


def list_backups(client, bucket: str, prefix: str):  # type: ignore[no-untyped-def]
    """Copies under a prefix, oldest first."""
    response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    items = [
        (obj["Key"], obj["Size"], obj["LastModified"])
        for obj in response.get("Contents", [])
        if obj["Key"].endswith(".tar.age")
    ]
    return sorted(items, key=lambda item: item[2])


def latest_key(client, bucket: str) -> str:  # type: ignore[no-untyped-def]
    """The newest copy in daily/."""
    items = list_backups(client, bucket, DAILY)
    return items[-1][0] if items else ""


def restore_into(settings: Settings, dump: Path, database: str) -> int:
    """Restore the dump into the named database inside the Postgres container."""
    print(f"restoring {dump.name} into database {database}")
    copy = subprocess.run(
        [
            "docker",
            "compose",
            "--file",
            settings.compose_file,
            "cp",
            str(dump),
            f"{settings.db_service}:/tmp/db.dump",
        ],
        cwd=settings.project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if copy.returncode != 0:
        print(f"could not copy the dump: {copy.stderr.strip()}", file=sys.stderr)
        return 1

    result = subprocess.run(
        [
            "docker",
            "compose",
            "--file",
            settings.compose_file,
            "exec",
            "--no-TTY",
            settings.db_service,
            "pg_restore",
            "--username",
            settings.db_user,
            "--dbname",
            database,
            "--clean",
            "--if-exists",
            "--no-owner",
            "/tmp/db.dump",
        ],
        cwd=settings.project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout or result.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
