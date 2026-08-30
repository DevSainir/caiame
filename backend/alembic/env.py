import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from core.config import get_settings
from models.accreditation import Accreditation  # noqa: F401  # imported so autogenerate sees it
from models.base import Base
from models.course import Course  # noqa: F401  # imported so autogenerate sees it
from models.course_benefit import CourseBenefit  # noqa: F401  # imported so autogenerate sees it
from models.course_question import CourseQuestion  # noqa: F401  # imported so autogenerate sees it
from models.course_unit import CourseUnit  # noqa: F401  # imported so autogenerate sees it
from models.lesson import Lesson  # noqa: F401  # imported so autogenerate sees it
from models.lesson_progress import LessonProgress  # noqa: F401  # imported so autogenerate sees it
from models.quiz import Quiz  # noqa: F401  # imported so autogenerate sees it
from models.quiz_attempt import (  # noqa: F401  # imported so autogenerate sees it
    QuizAttempt,
    QuizAttemptAnswer,
)
from models.quiz_question import (  # noqa: F401  # imported so autogenerate sees it
    QuizOption,
    QuizQuestion,
)
from models.refresh_token import RefreshToken  # noqa: F401  # imported so autogenerate sees it
from models.review import Review  # noqa: F401  # imported so autogenerate sees it
from models.specialization import Specialization  # noqa: F401  # imported so autogenerate sees it
from models.unit_progress import UnitProgress  # noqa: F401  # imported so autogenerate sees it
from models.user import User  # noqa: F401  # imported so autogenerate sees it

config = context.config
# A caller may point Alembic at another database (the integration test does); only fall
# back to the configured one when nobody has.
if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    """Run migrations on an already-open synchronous connection."""
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Open the async engine and hand a sync connection to Alembic."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_offline() -> None:
    """Emit SQL without a database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
