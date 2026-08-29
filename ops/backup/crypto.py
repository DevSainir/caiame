"""
Archive encryption through age.

Uses a key file rather than a passphrase: age's passphrase mode demands a terminal and
cannot run from a timer. The trust model is the one that was chosen — a single secret that
both encrypts and decrypts — only expressed as a file so the job runs unattended.
"""

import subprocess
from pathlib import Path


class EncryptionError(RuntimeError):
    """age refused to encrypt or decrypt."""


def encrypt(source: Path, target: Path, recipient: str) -> None:
    """Encrypt a file to the public half of the key."""
    _run(["age", "--encrypt", "--recipient", recipient, "--output", str(target), str(source)])


def decrypt(source: Path, target: Path, identity_file: Path) -> None:
    """Decrypt a file with the private half of the key."""
    _run(
        ["age", "--decrypt", "--identity", str(identity_file), "--output", str(target), str(source)]
    )


def _run(command: list[str]) -> None:
    """Run age and turn its refusal into a readable exception."""
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise EncryptionError(f"{' '.join(command[:2])}: {result.stderr.strip()}")
