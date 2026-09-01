"""watched time on lesson progress

Revision ID: 5a68b8aaf92d
Revises: 10185adecd7a
Create Date: 2026-09-01 18:07:37.139680
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5a68b8aaf92d"
down_revision: str | None = "10185adecd7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lesson_progress",
        sa.Column("last_position_sec", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "lesson_progress",
        sa.Column("watched_seconds", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("lesson_progress", "watched_seconds")
    op.drop_column("lesson_progress", "last_position_sec")
