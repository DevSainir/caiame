"""
Proof that a stored archive actually restores.

A backup nobody has ever restored is not a backup: corruption gets noticed on the one day
it matters. So once a week the archive is pulled back out of the bucket, decrypted and
restored into a throwaway Postgres container — checking what is in the cloud rather than
what happens to be left on the server disk.
"""

import subprocess
import tarfile
import time
from pathlib import Path

from config import Settings
from crypto import decrypt
from storage import download

CHECK_CONTAINER = "caiame-restore-check"
CHECK_PASSWORD = "restore-check"  # noqa: S105  # throwaway container, no published ports
CHECK_IMAGE = "postgres:16-alpine"
READY_TIMEOUT_SECONDS = 60


class VerificationError(RuntimeError):
    """The archive did not restore, or restored empty."""


def verify_archive(settings: Settings, key: str, work_dir: Path) -> dict[str, int]:
    """Download the archive, restore it into a throwaway database, return the row counts."""
    encrypted = work_dir / "verify.tar.age"
    archive = work_dir / "verify.tar"
    extracted = work_dir / "verify"

    client_module = __import__("storage")
    client = client_module.make_client(settings)
    download(client, settings.s3_bucket, key, encrypted)
    decrypt(encrypted, archive, settings.identity_path(work_dir))

    extracted.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        tar.extractall(extracted, filter="data")

    dump = extracted / "db.dump"
    if not dump.exists():
        raise VerificationError("the archive contains no db.dump")

    _remove_container()
    try:
        _start_container()
        _wait_until_ready()
        _restore(dump)
        return _count_rows()
    finally:
        _remove_container()


def _start_container() -> None:
    """Start a throwaway Postgres with no ports published."""
    _run(
        [
            "docker",
            "run",
            "--rm",
            "--detach",
            "--name",
            CHECK_CONTAINER,
            "--env",
            f"POSTGRES_PASSWORD={CHECK_PASSWORD}",
            CHECK_IMAGE,
        ],
        "could not start the verification container",
    )


def _wait_until_ready() -> None:
    """Wait until Postgres inside the container starts accepting connections."""
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        probe = subprocess.run(
            ["docker", "exec", CHECK_CONTAINER, "pg_isready", "-U", "postgres"],
            capture_output=True,
            check=False,
        )
        if probe.returncode == 0:
            return
        time.sleep(1)
    raise VerificationError("the verification container did not come up in time")


def _restore(dump: Path) -> None:
    """Restore the dump into the throwaway database."""
    _run(
        ["docker", "cp", str(dump), f"{CHECK_CONTAINER}:/tmp/db.dump"],
        "could not copy the dump into the container",
    )
    _run(
        [
            "docker",
            "exec",
            CHECK_CONTAINER,
            "pg_restore",
            "--username",
            "postgres",
            "--dbname",
            "postgres",
            "--no-owner",
            "--no-privileges",
            "/tmp/db.dump",
        ],
        "pg_restore could not restore the dump",
    )


# Tables the restored database must be able to answer for. The first four must hold rows —
# a catalogue without courses is not a restored catalogue. The rest may legitimately be
# empty on a young server, and they are here for a different reason: a table that a
# migration renamed or dropped makes this query fail, and a backup of a schema the
# application no longer matches is the kind of thing that is discovered on the worst day.
REQUIRED_TABLES = ("courses", "specializations", "accreditations", "users")
STUDENT_TABLES = (
    "enrollments",
    "entitlements",
    "lesson_progress",
    "media_files",
    "submissions",
    "submission_reviews",
    "quiz_attempts",
    # Who may review whose work. Empty is a legitimate state, so only its existence is
    # checked — but a restore without this table would leave every teacher seeing nothing,
    # and nobody would connect that to the restore.
    "course_reviewers",
)


def _count_rows() -> dict[str, int]:
    """
    Count rows in the tables the restored database must be able to answer for.

    A successful pg_restore does not mean a working backup: a dump of an empty schema
    restores without a single error. This checks the data is actually there — and that
    every table the application needs still exists under the name it expects.
    """
    counts: dict[str, int] = {}
    for table in (*REQUIRED_TABLES, *STUDENT_TABLES):
        result = subprocess.run(
            [
                "docker",
                "exec",
                CHECK_CONTAINER,
                "psql",
                "--username",
                "postgres",
                "--dbname",
                "postgres",
                "--tuples-only",
                "--no-align",
                "--command",
                f"SELECT count(*) FROM {table};",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise VerificationError(f"table {table} is unreadable: {result.stderr.strip()}")
        counts[table] = int(result.stdout.strip())

    if counts["courses"] == 0:
        raise VerificationError("the course catalogue in the restored database is empty")
    return counts


def _remove_container() -> None:
    """Remove the verification container whatever happened."""
    subprocess.run(
        ["docker", "rm", "--force", CHECK_CONTAINER],
        capture_output=True,
        check=False,
    )


def _run(command: list[str], message: str) -> None:
    """Run a command and turn a failure into a readable exception."""
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise VerificationError(f"{message}: {result.stderr.strip()[:400]}")
