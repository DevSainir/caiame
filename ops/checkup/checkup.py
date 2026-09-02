#!/usr/bin/env python3
"""
One command that asks production whether it is all right.

Monitoring proper needs somewhere to send an alarm, and that channel is not chosen yet.
This is the half that needs nobody: a person runs it — after a deploy, or when something
feels wrong — and gets one screen with the answers to the questions that are actually asked
when a site misbehaves. Every check prints what it saw, not just a verdict: «диск занят на
91%» is useful, «диск: плохо» is not.

Exit code is 1 when anything is wrong, so the day a notification channel appears, this
becomes its body without a rewrite.

    python3 ops/checkup/checkup.py [--url https://caiame.org]
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

# A daily copy that is older than this means the timer did not fire or the upload failed.
BACKUP_MAX_AGE = timedelta(hours=26)
# A certificate renews itself at thirty days; twenty means the renewal is not happening.
CERT_MIN_DAYS = 20
DISK_MIN_FREE_PERCENT = 15
HTTP_TIMEOUT = 15


@dataclass(frozen=True)
class Result:
    """What one check saw."""

    name: str
    ok: bool
    detail: str


def check_ready(url: str) -> Result:
    """The readiness endpoint: it really asks the database and the cache."""
    try:
        with urllib.request.urlopen(  # noqa: S310 - the address comes from the operator
            f"{url}/api/v1/health/ready", timeout=HTTP_TIMEOUT
        ) as answer:
            body = json.loads(answer.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return Result("readiness", False, f"no answer: {error}")
    parts = ", ".join(f"{name}: {'yes' if value else 'no'}" for name, value in body.items())
    return Result("readiness", body.get("status") == "ok", parts)


def check_home(url: str) -> Result:
    """The page itself, because an API in order and a blank site is a real combination."""
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as answer:  # noqa: S310
            code = answer.status
            size = len(answer.read())
    except (urllib.error.URLError, TimeoutError) as error:
        return Result("home page", False, f"no answer: {error}")
    return Result("home page", code == 200 and size > 0, f"{code}, {size} bytes")


def check_certificate(url: str) -> Result:
    """How long the certificate has left. Renewal is automatic — this is whether it works."""
    host = url.split("://", 1)[-1].split("/", 1)[0]
    try:
        with (
            socket.create_connection((host, 443), timeout=HTTP_TIMEOUT) as raw,
            ssl.create_default_context().wrap_socket(raw, server_hostname=host) as tls,
        ):
            not_after = tls.getpeercert()["notAfter"]  # type: ignore[index]
    except (OSError, ssl.SSLError) as error:
        return Result("certificate", False, f"unreadable: {error}")
    expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
    days = (expires - datetime.now(UTC)).days
    return Result("certificate", days >= CERT_MIN_DAYS, f"{days} days left")


def check_containers(project_dir: Path, compose_file: str) -> Result:
    """Every service up, and the ones with a healthcheck healthy."""
    try:
        raw = subprocess.run(
            ["docker", "compose", "-f", compose_file, "ps", "--format", "json"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        ).stdout
    except (subprocess.SubprocessError, FileNotFoundError) as error:
        return Result("containers", False, f"not asked: {error}")

    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not rows:
        return Result("containers", False, "none running")
    broken = [
        f"{row.get('Service')}: {row.get('State')}"
        for row in rows
        if row.get("State") != "running" or "unhealthy" in str(row.get("Health", ""))
    ]
    detail = ", ".join(broken) if broken else f"{len(rows)} running"
    return Result("containers", not broken, detail)


def check_disk(path: Path) -> Result:
    """Free space, because the two things that grow by themselves both end here."""
    usage = shutil.disk_usage(path)
    free_percent = round(usage.free * 100 / usage.total)
    return Result(
        "disk",
        free_percent >= DISK_MIN_FREE_PERCENT,
        f"{free_percent}% free of {usage.total // 1024**3} GB",
    )


def check_backup() -> Result:
    """
    The freshness of the newest daily copy.

    A backup that stopped being made is discovered on the day it is needed, which is the
    worst possible day for the discovery.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backup"))
    try:
        from config import Settings
        from storage import DAILY, make_client

        settings = Settings.from_environment()
        client = make_client(settings)
        listing = client.list_objects_v2(Bucket=settings.s3_bucket, Prefix=DAILY)
    # Deliberately broad: no credentials, no network, a changed bucket — from here they
    # are one answer, "we do not know whether there is a copy", and that answer is bad news.
    except Exception as error:
        return Result("backup", False, f"not checked: {error}")

    objects = listing.get("Contents", [])
    if not objects:
        return Result("backup", False, "nothing in storage")
    newest = max(objects, key=lambda item: item["LastModified"])
    age = datetime.now(UTC) - newest["LastModified"].astimezone(UTC)
    hours = round(age.total_seconds() / 3600)
    size = newest["Size"] // 1024
    return Result("backup", age < BACKUP_MAX_AGE, f"{hours} h ago, {size} KB")


def main() -> int:
    """Run every check and print one screen."""
    parser = argparse.ArgumentParser(description="Ask production whether it is all right.")
    parser.add_argument("--url", default="https://caiame.org", help="Site address.")
    parser.add_argument("--dir", default="/opt/caiame", type=Path, help="Project directory.")
    parser.add_argument("--compose-file", default="docker-compose.prod.yml")
    parser.add_argument("--skip-backup", action="store_true", help="Do not ask storage.")
    args = parser.parse_args()

    checks = [
        check_ready(args.url),
        check_home(args.url),
        check_certificate(args.url),
        check_containers(args.dir, args.compose_file),
        check_disk(args.dir if args.dir.exists() else Path.cwd()),
    ]
    if not args.skip_backup:
        checks.append(check_backup())

    width = max(len(check.name) for check in checks)
    for check in checks:
        print(f"{'ok  ' if check.ok else 'BAD '} {check.name.ljust(width)}  {check.detail}")

    bad = [check.name for check in checks if not check.ok]
    print()
    print("All good." if not bad else f"Needs attention: {', '.join(bad)}.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
