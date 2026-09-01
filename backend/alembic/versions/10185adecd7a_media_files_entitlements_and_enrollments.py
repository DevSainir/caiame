"""media files, entitlements and enrollments

Revision ID: 10185adecd7a
Revises: c7501e02a7a6
Create Date: 2026-09-01 15:47:42.951371
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "10185adecd7a"
down_revision: str | None = "c7501e02a7a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_files",
        sa.Column("bucket", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=500), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "READY", name="media_status", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("uploaded_by_id", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_media_files_status"), "media_files", ["status"], unique=False)
    op.create_table(
        "entitlements",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=True),
        sa.Column(
            "source",
            sa.Enum(
                "PURCHASE",
                "SUBSCRIPTION",
                "MANUAL",
                "PROMO",
                name="access_source",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_by_id", sa.UUID(), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=False),
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
        sa.ForeignKeyConstraint(["granted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_entitlements_course_id"), "entitlements", ["course_id"], unique=False)
    op.create_index(op.f("ix_entitlements_user_id"), "entitlements", ["user_id"], unique=False)
    op.create_table(
        "enrollments",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_lesson_id", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(["last_lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "course_id", name="uq_enrollment_student"),
    )
    op.create_index(op.f("ix_enrollments_course_id"), "enrollments", ["course_id"], unique=False)
    op.create_index(op.f("ix_enrollments_user_id"), "enrollments", ["user_id"], unique=False)
    op.add_column("lessons", sa.Column("media_file_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_lessons_media_file",
        "lessons",
        "media_files",
        ["media_file_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("lessons", "asset_url")


def downgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column("asset_url", sa.VARCHAR(length=500), nullable=False, server_default=""),
    )
    op.drop_constraint("fk_lessons_media_file", "lessons", type_="foreignkey")
    op.drop_column("lessons", "media_file_id")
    op.drop_index(op.f("ix_enrollments_user_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_course_id"), table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_index(op.f("ix_entitlements_user_id"), table_name="entitlements")
    op.drop_index(op.f("ix_entitlements_course_id"), table_name="entitlements")
    op.drop_table("entitlements")
    op.drop_index(op.f("ix_media_files_status"), table_name="media_files")
    op.drop_table("media_files")
