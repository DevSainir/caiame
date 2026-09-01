"""course reviewers

Revision ID: 8b4304df91a4
Revises: eed2f41c5c45
Create Date: 2026-09-01 22:02:25.766878
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8b4304df91a4"
down_revision: str | None = "eed2f41c5c45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "course_reviewers",
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "user_id", name="uq_course_reviewer"),
    )
    op.create_index(
        op.f("ix_course_reviewers_course_id"), "course_reviewers", ["course_id"], unique=False
    )
    op.create_index(
        op.f("ix_course_reviewers_user_id"), "course_reviewers", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_course_reviewers_user_id"), table_name="course_reviewers")
    op.drop_index(op.f("ix_course_reviewers_course_id"), table_name="course_reviewers")
    op.drop_table("course_reviewers")
