"""create roster_uploads members import_issues

Revision ID: 1b4d2ba03ea1
Revises:
Create Date: 2026-07-29 10:34:20.116867

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1b4d2ba03ea1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roster_uploads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "succeeded",
                "failed",
                name="upload_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("accepted_rows", sa.Integer(), nullable=False),
        sa.Column("rejected_rows", sa.Integer(), nullable=False),
        sa.Column("ruleset_version", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("roster_uploads", schema=None) as batch_op:
        batch_op.create_index(
            "uq_roster_uploads_one_active",
            ["is_active"],
            unique=True,
            sqlite_where=sa.text("is_active = 1"),
            postgresql_where=sa.text("is_active IS TRUE"),
        )

    op.create_table(
        "import_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("upload_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("field", sa.String(length=64), nullable=True),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "error",
                "warning",
                name="issue_severity",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["upload_id"], ["roster_uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("import_issues", schema=None) as batch_op:
        batch_op.create_index("ix_import_issues_upload_id", ["upload_id"], unique=False)

    op.create_table(
        "members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("upload_id", sa.Uuid(), nullable=False),
        sa.Column("dodid", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("rank", sa.String(length=64), nullable=True),
        sa.Column(
            "personnel_type",
            sa.Enum(
                "enlisted",
                "officer",
                name="personnel_type",
                native_enum=False,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("afsc", sa.String(length=32), nullable=False),
        sa.Column("normalized_afsc", sa.String(length=32), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["upload_id"], ["roster_uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("members", schema=None) as batch_op:
        batch_op.create_index("ix_members_normalized_afsc", ["normalized_afsc"], unique=False)
        batch_op.create_index("ix_members_upload_id", ["upload_id"], unique=False)
        batch_op.create_index(
            "ix_members_upload_name_afsc",
            ["upload_id", "display_name", "normalized_afsc"],
            unique=False,
        )
        batch_op.create_index(
            "uq_members_upload_dodid",
            ["upload_id", "dodid"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("members", schema=None) as batch_op:
        batch_op.drop_index("uq_members_upload_dodid")
        batch_op.drop_index("ix_members_upload_name_afsc")
        batch_op.drop_index("ix_members_upload_id")
        batch_op.drop_index("ix_members_normalized_afsc")

    op.drop_table("members")
    with op.batch_alter_table("import_issues", schema=None) as batch_op:
        batch_op.drop_index("ix_import_issues_upload_id")

    op.drop_table("import_issues")
    with op.batch_alter_table("roster_uploads", schema=None) as batch_op:
        batch_op.drop_index(
            "uq_roster_uploads_one_active",
            sqlite_where=sa.text("is_active = 1"),
            postgresql_where=sa.text("is_active IS TRUE"),
        )

    op.drop_table("roster_uploads")
