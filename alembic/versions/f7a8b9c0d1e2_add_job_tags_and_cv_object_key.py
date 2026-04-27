"""add job tags, tag map, and application cv_object_key

Revision ID: f7a8b9c0d1e2
Revises: e19b4c7a1d2e
Create Date: 2026-04-28 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e19b4c7a1d2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_job_tags_slug"),
    )

    op.create_table(
        "job_tag_map",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["job_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id", "tag_id"),
    )

    op.add_column(
        "applications",
        sa.Column("cv_object_key", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("applications", "cv_object_key")
    op.drop_table("job_tag_map")
    op.drop_table("job_tags")
