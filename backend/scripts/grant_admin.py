"""
Make an administrator: create the account, or raise an existing one to that rung.

A separate command from `seed.py` because the seeder deliberately creates no accounts in
production — its password is committed to this repository. An administrator still has to
exist there: nothing in the interface promotes the first account, and the ladder in
`core/access.py` answers 403 to everybody else. This is the command that makes one.

The password is asked for, not passed in: an argument lands in shell history and in the
process list, where every other account on the host can read it. `ADMIN_PASSWORD` in the
environment is the fallback for a run without a terminal.

    python scripts/grant_admin.py you@example.org --name "Full Name"

An existing account is promoted and keeps its password unless `--reset-password` says
otherwise. Running the command twice changes nothing the second time.
"""

import argparse
import asyncio
import getpass
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import session_factory
from core.security import hash_password
from models.enums import UserRole
from models.refresh_token import RefreshToken
from models.user import User

# Argon2 already makes an offline guess expensive; length is what makes an online one
# hopeless. This account publishes courses and grants access, so it gets the longer floor.
MIN_PASSWORD_LENGTH = 12
ENV_VARIABLE = "ADMIN_PASSWORD"


def read_password() -> str:
    """
    Get the password from the terminal, or from the environment when there is none.

    Asked twice on a terminal: a typo here locks out the only account that can undo it.
    """
    from_env = os.environ.get(ENV_VARIABLE)
    if from_env is not None:
        password = from_env
    elif sys.stdin.isatty():
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Repeat: "):
            raise SystemExit("passwords do not match, nothing was changed")
    else:
        raise SystemExit(f"no terminal to ask on; pass the password in {ENV_VARIABLE}")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    return password


async def revoke_sessions(session: AsyncSession, user_id: UUID) -> int:
    """
    End every live session of an account whose password just changed.

    A refresh token outlives the password it was issued under: without this, changing a
    leaked account's password leaves whoever leaked it signed in for another week.
    """
    live = (
        await session.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
            )
        )
    ).all()
    now = datetime.now(UTC)
    for token in live:
        token.revoked_at = now
    return len(live)


async def main(email: str, full_name: str, reset_password: bool) -> None:
    """Create or promote one account, and say exactly what changed."""
    address = email.strip().lower()
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.email == address))

        if user is None:
            session.add(
                User(
                    email=address,
                    password_hash=hash_password(read_password()),
                    full_name=full_name,
                    role=UserRole.ADMIN,
                )
            )
            await session.commit()
            print(f"created administrator {address}")
            return

        changed: list[str] = []
        if user.role is not UserRole.ADMIN:
            changed.append(f"role {user.role} -> admin")
            user.role = UserRole.ADMIN
        if not user.is_active:
            changed.append("reactivated")
            user.is_active = True
        if full_name and user.full_name != full_name:
            changed.append("name")
            user.full_name = full_name
        if reset_password:
            user.password_hash = hash_password(read_password())
            revoked = await revoke_sessions(session, user.id)
            changed.append(f"password (revoked {revoked} sessions)")
        await session.commit()

    print(f"{address}: {', '.join(changed) if changed else 'already an administrator'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or promote an administrator account.")
    parser.add_argument("email", help="address of the account")
    parser.add_argument("--name", default="", help="display name, set on creation")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="also set a new password on an existing account and end its sessions",
    )
    args = parser.parse_args()
    asyncio.run(main(args.email, args.name, args.reset_password))
