"""Backup job settings, read from the environment and from the .env next to the project."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ENV_FILE = Path("/opt/caiame/.env")


def load_env_file(path: Path) -> dict[str, str]:
    """Read a .env into a dict. No interpolation: values are taken exactly as written."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


@dataclass(frozen=True)
class Settings:
    """Everything the job needs: where the database is, where to put copies, what encrypts them."""

    project_dir: Path
    compose_file: str
    db_service: str
    db_user: str
    db_name: str
    secrets_file: Path
    age_recipient: str
    age_identity_file: Path
    age_secret: str
    s3_endpoint: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    s3_region: str
    work_dir: Path

    @classmethod
    def from_environment(cls) -> "Settings":
        """Assemble settings: the environment wins over the project .env."""
        project_dir = Path(os.environ.get("CAIAME_DIR", "/opt/caiame"))
        env_file = Path(os.environ.get("CAIAME_ENV_FILE", str(project_dir / ".env")))
        env = {**load_env_file(env_file), **os.environ}

        missing = [
            key
            for key in (
                "S3_CLOUDFARE_ACCESS_KEY",
                "S3_CLOUDFARE_SECRET_ACCESS_KEY",
                "S3_CLOUDFARE_URL",
                "S3_CLOUDFARE_BUCKET",
            )
            if not env.get(key)
        ]
        if missing:
            raise SystemExit(f"missing required settings: {', '.join(missing)}")

        identity = Path(env.get("BACKUP_AGE_IDENTITY", str(project_dir / "backup-age.key")))
        secret = env.get("BACKUP_AGE_SECRET", "")
        recipient = env.get("BACKUP_AGE_RECIPIENT", "")
        if not recipient and identity.exists():
            recipient = _recipient_from_identity(identity)
        if not recipient and secret:
            recipient = _recipient_from_secret(secret)
        if not recipient:
            raise SystemExit(
                "BACKUP_AGE_RECIPIENT is unset, BACKUP_AGE_SECRET is empty and no key "
                f"was found at {identity}: there is nothing to encrypt with"
            )

        return cls(
            project_dir=project_dir,
            compose_file=env.get("CAIAME_COMPOSE_FILE", "docker-compose.prod.yml"),
            db_service=env.get("CAIAME_DB_SERVICE", "db"),
            db_user=env.get("POSTGRES_USER", "caiame"),
            db_name=env.get("POSTGRES_DB", "caiame"),
            secrets_file=env_file,
            age_recipient=recipient,
            age_identity_file=identity,
            age_secret=secret,
            s3_endpoint=env["S3_CLOUDFARE_URL"],
            s3_bucket=env["S3_CLOUDFARE_BUCKET"],
            s3_access_key=env["S3_CLOUDFARE_ACCESS_KEY"],
            s3_secret_key=env["S3_CLOUDFARE_SECRET_ACCESS_KEY"],
            s3_region=env.get("CLOUDFARE_DEFAULT_REGION_NAME", "auto"),
            work_dir=Path(env.get("BACKUP_WORK_DIR", "/tmp/caiame-backup")),
        )

    def identity_path(self, work_dir: Path) -> Path:
        """
        A key file for age to decrypt with.

        The key normally lives in a file on the server. A workstation may instead carry it
        as BACKUP_AGE_SECRET in its own .env, in which case it is written out to a private
        file for the length of the run — age reads identities from files, not from the
        environment.
        """
        if self.age_identity_file.exists():
            return self.age_identity_file
        if not self.age_secret:
            raise SystemExit(
                f"no key: {self.age_identity_file} is missing and BACKUP_AGE_SECRET is empty"
            )
        work_dir.mkdir(parents=True, exist_ok=True)
        written = work_dir / "identity.key"
        written.write_text(f"{self.age_secret}\n", encoding="utf-8")
        written.chmod(0o600)
        return written


def _recipient_from_secret(secret: str) -> str:
    """Derive the public half from a secret key, so only one value has to be configured."""
    result = subprocess.run(
        ["age-keygen", "-y"], input=f"{secret}\n", capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"BACKUP_AGE_SECRET is not a valid age key: {result.stderr.strip()}")
    return result.stdout.strip()


def _recipient_from_identity(identity: Path) -> str:
    """Read the public half out of the age key file, so it is not configured twice."""
    for line in identity.read_text(encoding="utf-8").splitlines():
        if line.startswith("# public key: "):
            return line.removeprefix("# public key: ").strip()
    return ""
