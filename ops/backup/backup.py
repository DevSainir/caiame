#!/usr/bin/env python3
"""
Back the database and the secrets up to Cloudflare R2.

Every run puts an archive in daily/. On Sundays the same copy appears in weekly/, on the
first of the month in monthly/; the copying is done by the storage itself, so all three
objects are identical byte for byte. Retention is set by lifecycle rules in R2 — nothing
is deleted here, or the rule would live in two places and drift.

The archive holds two files: the database dump and the server .env. Without the secrets a
restored database is useless: neither the sessions nor the access to the database itself
can be brought back.
"""

import argparse
import shutil
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from config import Settings
from crypto import encrypt
from storage import DAILY, MONTHLY, WEEKLY, copy_within_bucket, make_client, upload
from verify import verify_archive

SUNDAY = 6


def main() -> int:
    """Dump, encrypt, upload and — on Sundays — prove the copy restores."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="verify by restoring, right now")
    parser.add_argument("--no-verify", action="store_true", help="skip the verification")
    options = parser.parse_args()

    settings = Settings.from_environment()
    now = datetime.now(UTC)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    name = f"caiame-{stamp}.tar.age"

    work_dir = settings.work_dir / stamp
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        archive = build_archive(settings, work_dir)
        encrypted = work_dir / name
        encrypt(archive, encrypted, settings.age_recipient)
        log(f"archive encrypted, {encrypted.stat().st_size / 1024:.0f} KB")

        client = make_client(settings)
        daily_key = f"{DAILY}{name}"
        upload(client, settings.s3_bucket, encrypted, daily_key)
        log(f"uploaded {daily_key}")

        is_weekly = now.weekday() == SUNDAY
        is_monthly = now.day == 1
        for enabled, prefix in ((is_weekly, WEEKLY), (is_monthly, MONTHLY)):
            if not enabled:
                continue
            copy_within_bucket(client, settings.s3_bucket, daily_key, f"{prefix}{name}")
            log(f"copied to {prefix}{name}")

        should_verify = options.verify or (is_weekly and not options.no_verify)
        if should_verify:
            source_key = f"{WEEKLY}{name}" if is_weekly else daily_key
            log(f"verifying by restoring {source_key}")
            counts = verify_archive(settings, source_key, work_dir)
            log("restored: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
        else:
            log("no restore verification scheduled today")

        log("done")
        return 0
    except Exception as error:  # the timer needs an exit code, not a traceback
        log(f"FAILED: {error}")
        return 1
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def build_archive(settings: Settings, work_dir: Path) -> Path:
    """Dump the database and pack it together with the secrets into one tar."""
    dump = work_dir / "db.dump"
    command = [
        "docker",
        "compose",
        "--file",
        settings.compose_file,
        "exec",
        "--no-TTY",
        settings.db_service,
        "pg_dump",
        "--username",
        settings.db_user,
        "--format",
        "custom",
        settings.db_name,
    ]
    with dump.open("wb") as target:
        result = subprocess.run(
            command, cwd=settings.project_dir, stdout=target, stderr=subprocess.PIPE, check=False
        )
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr.decode().strip()[:400]}")
    if dump.stat().st_size == 0:
        raise RuntimeError("pg_dump produced an empty file")
    log(f"database dump {dump.stat().st_size / 1024:.0f} KB")

    archive = work_dir / "archive.tar"
    with tarfile.open(archive, "w") as tar:
        tar.add(dump, arcname="db.dump")
        if settings.secrets_file.exists():
            tar.add(settings.secrets_file, arcname="env")
        else:
            log(f"warning: {settings.secrets_file} is missing, the archive will carry no secrets")
    return archive


def log(message: str) -> None:
    """One log line. The timer sends it to systemd, which is where it gets read."""
    print(f"[{datetime.now(UTC).strftime('%H:%M:%S')}] {message}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
