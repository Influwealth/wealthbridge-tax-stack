"""add analytics_snapshots table

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_type", sa.String(50), nullable=False),  # "dashboard" | "forecast" | "optimizer"
        sa.Column("entity_name", sa.String(255), nullable=True),
        sa.Column("tax_year", sa.Integer(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),   # JSON blob
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_snapshots_type", "analytics_snapshots", ["snapshot_type"])
    op.create_index("ix_analytics_snapshots_entity", "analytics_snapshots", ["entity_name"])


def downgrade() -> None:
    op.drop_table("analytics_snapshots")
