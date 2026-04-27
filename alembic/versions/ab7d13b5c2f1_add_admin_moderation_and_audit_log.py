"""add admin moderation and audit log

Revision ID: ab7d13b5c2f1
Revises: 575c64810fd3
Create Date: 2026-04-27 13:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ab7d13b5c2f1"
down_revision: Union[str, Sequence[str], None] = "575c64810fd3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE TYPE job_moderation_status AS ENUM ('pending', 'approved', 'rejected')")

    op.add_column(
        "jobs",
        sa.Column(
            "moderation_status",
            sa.Enum("pending", "approved", "rejected", name="job_moderation_status"),
            server_default=sa.text("'pending'::job_moderation_status"),
            nullable=False,
        ),
    )
    op.add_column("jobs", sa.Column("moderation_note", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("moderated_by_admin_user_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_jobs_moderation_status"), "jobs", ["moderation_status"], unique=False)
    op.create_foreign_key(
        "fk_jobs_moderated_by_admin_user_id_users",
        "jobs",
        "users",
        ["moderated_by_admin_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_audit_logs_action"), "admin_audit_logs", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_admin_audit_logs_admin_user_id"),
        "admin_audit_logs",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_audit_logs_target_id"), "admin_audit_logs", ["target_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_admin_audit_logs_target_id"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_admin_user_id"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_action"), table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")

    op.drop_constraint("fk_jobs_moderated_by_admin_user_id_users", "jobs", type_="foreignkey")
    op.drop_index(op.f("ix_jobs_moderation_status"), table_name="jobs")
    op.drop_column("jobs", "moderated_at")
    op.drop_column("jobs", "moderated_by_admin_user_id")
    op.drop_column("jobs", "moderation_note")
    op.drop_column("jobs", "moderation_status")

    op.execute("DROP TYPE job_moderation_status")
