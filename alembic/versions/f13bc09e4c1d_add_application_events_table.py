"""add application events table

Revision ID: f13bc09e4c1d
Revises: ab7d13b5c2f1
Create Date: 2026-04-27 19:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f13bc09e4c1d"
down_revision: Union[str, Sequence[str], None] = "ab7d13b5c2f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "application_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum(
                "SUBMITTED",
                "REVIEWING",
                "REJECTED",
                "ACCEPTED",
                name="application_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "SUBMITTED",
                "REVIEWING",
                "REJECTED",
                "ACCEPTED",
                name="application_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_events_application_id"),
        "application_events",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_events_actor_user_id"),
        "application_events",
        ["actor_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_application_events_actor_user_id"), table_name="application_events")
    op.drop_index(op.f("ix_application_events_application_id"), table_name="application_events")
    op.drop_table("application_events")
