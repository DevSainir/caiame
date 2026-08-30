"""deferrable position constraints

Revision ID: c7501e02a7a6
Revises: 8a25c974eada
Create Date: 2026-08-30 21:17:22.180811
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c7501e02a7a6"
down_revision: str | None = "8a25c974eada"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Moving a lesson or a module swaps two positions. Both rows are written in one
# transaction, and in the middle of that swap they briefly share a position: an immediate
# unique check refuses it, a deferred one sees only the finished order.
CONSTRAINTS = (
    ("lessons", "uq_lesson_position", ["unit_id", "position"]),
    ("course_units", "uq_unit_position", ["course_id", "kind", "position"]),
)


def upgrade() -> None:
    """Let the position constraints be checked at commit instead of per statement."""
    for table, name, columns in CONSTRAINTS:
        op.drop_constraint(name, table, type_="unique")
        op.create_unique_constraint(name, table, columns, deferrable=True, initially="DEFERRED")


def downgrade() -> None:
    """Back to an immediate check. Reordering breaks again — that is what it was."""
    for table, name, columns in CONSTRAINTS:
        op.drop_constraint(name, table, type_="unique")
        op.create_unique_constraint(name, table, columns)
