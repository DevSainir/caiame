"""cycles: audience instead of difficulty

Revision ID: 8b1c7d2e4a90
Revises: 3cfd1266e84f
Create Date: 2026-08-29 12:10:00.000000

The catalogue moved from nine medical fields graded by difficulty to six training cycles,
each 72 hours under one credit scheme and admitting one profession. Difficulty is gone from
the course and the cycle now carries its audience.

The retired catalogue rows go with it: they are seed content, they name fields the academy
no longer teaches, and every one of them points at a specialization that is being dropped.
`scripts/seed.py` refills the tables with the new cycles.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8b1c7d2e4a90"
down_revision: str | None = "3cfd1266e84f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDIENCE = sa.Enum("DOCTOR", "NURSE", name="audience", native_enum=False, length=20)
DIFFICULTY = sa.Enum(
    "BEGINNER", "INTERMEDIATE", "ADVANCED", name="difficulty_level", native_enum=False, length=20
)


def upgrade() -> None:
    # Courses first: they hold the foreign key into the taxonomies being emptied.
    op.execute(sa.text("DELETE FROM courses"))
    op.execute(sa.text("DELETE FROM specializations"))
    op.execute(sa.text("DELETE FROM accreditations"))

    op.add_column(
        "specializations",
        sa.Column("audience", AUDIENCE, nullable=False, server_default="DOCTOR"),
    )
    # The default exists only to fill rows that predate the column; the model sets it.
    op.alter_column("specializations", "audience", server_default=None)
    op.create_index(
        op.f("ix_specializations_audience"), "specializations", ["audience"], unique=False
    )

    op.drop_index(op.f("ix_courses_difficulty"), table_name="courses")
    op.drop_column("courses", "difficulty")


def downgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("difficulty", DIFFICULTY, nullable=False, server_default="BEGINNER"),
    )
    op.alter_column("courses", "difficulty", server_default=None)
    op.create_index(op.f("ix_courses_difficulty"), "courses", ["difficulty"], unique=False)

    op.drop_index(op.f("ix_specializations_audience"), table_name="specializations")
    op.drop_column("specializations", "audience")
