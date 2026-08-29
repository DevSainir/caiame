"""
Wipe the catalogue so `seed.py` can lay down a new one.

A separate command rather than a step inside the seeder or a data migration: emptying the
catalogue is an operator's decision, not something a deploy should do on its own. Courses
cascade into their outline, questions, reasons, reviews and everybody's progress, so this
is the one script here that can destroy work.

Refuses to run in production without `--force`, and says out loud what it removed.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.db import session_factory
from models.accreditation import Accreditation
from models.course import Course
from models.review import Review
from models.specialization import Specialization
from models.unit_progress import UnitProgress

# Courses first: the taxonomies below them are pointed at by their foreign keys.
TABLES = (Course, Specialization, Accreditation)


async def count(session: AsyncSession, model: type) -> int:
    """How many rows this table holds right now."""
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def main(force: bool) -> None:
    """Delete the catalogue and everything hanging off it."""
    if get_settings().environment == "production" and not force:
        print("refusing to wipe the catalogue in production; pass --force if you mean it")
        raise SystemExit(1)

    async with session_factory() as session:
        reviews = await count(session, Review)
        progress = await count(session, UnitProgress)
        removed = {}
        for model in TABLES:
            removed[model.__tablename__] = await count(session, model)
            await session.execute(delete(model))
        await session.commit()

    summary = ", ".join(f"{table}: {rows}" for table, rows in removed.items())
    print(f"removed {summary}; cascaded {reviews} reviews and {progress} progress rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="allow this in production too")
    asyncio.run(main(parser.parse_args().force))
